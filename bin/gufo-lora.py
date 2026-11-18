#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["gguf==0.19.0", "numpy==2.5.4"]
# ///
"""Build Gufo-readable shards from stock reflinks and the pinned Huihui v2 LoRA."""
import argparse
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import urlopen
import shutil

import gguf
import numpy as np

ADAPTER = Path("nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA/HUIHUI-V2-Qwen3.8-Flash-Next-LoRA-F32.gguf")
DIGEST = "349022ca699f47205837b45f99e8a372077c0a1428920603d00b3b80bb31ee0f"


class TargetReader(gguf.GGUFReader):
    # gguf 0.19 cannot decode IQ4_XS's two Q2_0 experts. Only map LoRA targets.
    def _build_tensors(self, start_offs, fields):
        suffixes = (b".ssm_out.weight", b".attn_output.weight", b".ffn_down_shexp.weight")
        super()._build_tensors(start_offs, [f for f in fields if bytes(f.parts[1]).endswith(suffixes)])


def q6_encoder():
    import llama_cpp

    library = Path(llama_cpp.__file__).parent / "lib/libggml-base.so"
    encode = ctypes.CDLL(str(library)).quantize_row_q6_K_ref
    encode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
    encode.restype = None
    return encode


def merge(shards, adapter):
    factors = {tensor.name: tensor.data for tensor in adapter.tensors}
    if len(factors) != 192 or adapter.fields["adapter.lora.alpha"].contents() != 1:
        raise ValueError("Expected 96 rank-one updates at scale 1")
    encode_q6 = None
    for shard in shards:
        reader = TargetReader(shard, mode="r+")
        for tensor in reader.tensors:
            if tensor.name + ".lora_a" not in factors:
                continue
            a = factors.pop(tensor.name + ".lora_a")
            b = factors.pop(tensor.name + ".lora_b")
            width, height = map(int, tensor.shape)
            if (tensor.tensor_type not in (gguf.GGMLQuantizationType.Q8_0, gguf.GGMLQuantizationType.Q6_K)
                    or a.shape != (1, width) or b.shape != (height, 1)):
                raise ValueError(f"Incompatible tensor: {tensor.name}")
            for row in range(0, height, 128):
                block = slice(row, row + 128)
                weights = gguf.dequantize(tensor.data[block], tensor.tensor_type)
                weights += b[block] * a
                if tensor.tensor_type == gguf.GGMLQuantizationType.Q6_K:
                    if encode_q6 is None:
                        encode_q6 = q6_encoder()
                    values = np.ascontiguousarray(weights, dtype=np.float32)
                    encode_q6(values.ctypes.data, tensor.data[block].ctypes.data, values.size)
                else:
                    tensor.data[block] = gguf.quantize(weights, tensor.tensor_type)
    if factors:
        raise ValueError(f"Missing {len(factors)} adapter factors in stock shards")


def verify(path, digest):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
            raise ValueError(f"SHA-256 mismatch: {path}")


def fetch_adapter(models):
    path = models / ADAPTER
    if path.exists():
        verify(path, DIGEST)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    revision = "dee8e0177e4e61efdaa3fb7128c40d6ab7a085d4"
    url = f"https://huggingface.co/{ADAPTER.parent}/resolve/{revision}/{ADAPTER.name}"
    with tempfile.NamedTemporaryFile(dir=path.parent) as download:
        with urlopen(url, timeout=60) as response:
            shutil.copyfileobj(response, download)
        download.flush()
        verify(Path(download.name), DIGEST)
        try:
            os.link(download.name, path)
        except FileExistsError:
            verify(path, DIGEST)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quant", choices=["UD-Q4_K_XL", "UD-IQ4_XS"])
    quant = parser.parse_args().quant
    models = Path(os.environ.get("MODELS_DIR", "/home/bogdan/models")).resolve()
    adapter = fetch_adapter(models)
    output = adapter.parent / (quant + "-d9620119")
    if output.exists():
        raise FileExistsError(output)
    stock = models / "unsloth/Qwen3.8-Flash-Next-GGUF" / quant
    shards = sorted(stock.glob("*.gguf"))
    if len(shards) != 4:
        raise ValueError("Expected four stock GGUF shards")
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        staging = Path(temporary) / "shards"
        staging.mkdir()
        subprocess.run(["cp", "--reflink=always", "--", *shards, staging], check=True)
        merge(sorted(staging.glob("*.gguf")), gguf.GGUFReader(adapter))
        profile = "lora" if quant == "UD-Q4_K_XL" else "iq4-xs-lora"
        manifest = Path(__file__).resolve().parents[1] / f"config/weights/gufo-{profile}.tsv"
        for row in manifest.read_text().splitlines():
            digest, _, filename, *_ = row.split("\t")
            target = models / filename
            verify(staging / target.name if target.parent == output else target, digest)
        staging.rename(output)
    print(output)


if __name__ == "__main__":
    main()
