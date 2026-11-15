"""Compare a patched split GGUF with its stock source: metadata, layout, and which tensors changed and how."""
import re
import sys
from pathlib import Path

import gguf
import numpy as np

TARGET = re.compile(r"blk\.(\d+)\.(ssm_out|attn_output|ffn_down_shexp)\.weight$")


def load(directory):
    return [(path.name, gguf.GGUFReader(str(path))) for path in sorted(Path(directory).glob("*.gguf"))]


def q8_0(tensor):
    """Dequantise Q8_0: blocks of one float16 scale and 32 int8 values."""
    blocks = np.asarray(tensor.data).reshape(-1, 34)
    scale = blocks[:, :2].copy().view(np.float16).astype(np.float32)
    values = blocks[:, 2:].view(np.int8).astype(np.float32) * scale
    return values.reshape(tuple(int(d) for d in reversed(tensor.shape.tolist())))


def same_bytes(a, b):
    # The n-gram tensor is 28.8 GB: a whole-tensor comparison would allocate as much scratch RAM.
    a = np.asarray(a).view(np.uint8).reshape(-1)
    b = np.asarray(b).view(np.uint8).reshape(-1)
    chunk = 8 * 1024 * 1024
    return a.size == b.size and all(np.array_equal(a[i:i + chunk], b[i:i + chunk]) for i in range(0, a.size, chunk))


stock, patched = load(sys.argv[1]), load(sys.argv[2])
assert [n for n, _ in stock] == [n for n, _ in patched], "shard names differ"
problems, changed, total = [], [], 0
for (name, a), (_, b) in zip(stock, patched):
    keys_a = [k for k in a.fields if not k.startswith("GGUF.")]
    keys_b = [k for k in b.fields if not k.startswith("GGUF.")]
    if keys_a != keys_b:
        problems.append(f"{name}: metadata keys differ: only stock {sorted(set(keys_a) - set(keys_b))}, only patched {sorted(set(keys_b) - set(keys_a))}, order equal {sorted(keys_a) == sorted(keys_b)}")
    for key in set(keys_a) & set(keys_b):
        fa, fb = a.fields[key], b.fields[key]
        if [t for t in fa.types] != [t for t in fb.types] or b"".join(bytes(p) for p in fa.parts) != b"".join(bytes(p) for p in fb.parts):
            problems.append(f"{name}: metadata value differs: {key}")
    if [t.name for t in a.tensors] != [t.name for t in b.tensors]:
        problems.append(f"{name}: tensor names or order differ")
        continue
    for ta, tb in zip(a.tensors, b.tensors):
        total += 1
        if ta.tensor_type != tb.tensor_type or ta.shape.tolist() != tb.shape.tolist() or ta.n_bytes != tb.n_bytes:
            problems.append(f"{name}: layout differs: {ta.name} {ta.tensor_type.name}{ta.shape.tolist()} -> {tb.tensor_type.name}{tb.shape.tolist()}")
            continue
        if not same_bytes(ta.data, tb.data):
            changed.append((ta, tb))
    print(f"{name}: {len(a.tensors)} tensors compared", flush=True)

print(f"\n{total} tensors, {len(changed)} changed by content, {len(problems)} problems")
for problem in problems:
    print("PROBLEM", problem)
unexpected = [ta.name for ta, _ in changed if not TARGET.search(ta.name)]
print("changed tensors outside the three target families:", unexpected or "none")
expected = {t.name for _, reader in stock for t in reader.tensors if TARGET.search(t.name)}
missing = expected - {ta.name for ta, _ in changed}
print("target tensors left unchanged:", sorted(missing) or "none")
families = {}
for ta, tb in changed:
    match = TARGET.search(ta.name)
    if not match or ta.tensor_type != gguf.GGMLQuantizationType.Q8_0:
        continue
    wa, wb = q8_0(ta), q8_0(tb)
    delta = wb - wa
    # Top singular value by power iteration: the share of the change that lies in one direction.
    v = np.random.default_rng(0).standard_normal(delta.shape[1]).astype(np.float32)
    for _ in range(40):
        v = delta.T @ (delta @ v)
        v /= np.linalg.norm(v)
    top = float(np.linalg.norm(delta @ v) ** 2 / np.linalg.norm(delta) ** 2)
    families.setdefault(match.group(2), []).append((float(np.linalg.norm(delta) / np.linalg.norm(wa)), top))
print("\nper family: count, relative change |patched - stock| / |stock|, share of the change in its top singular direction")
for family, rows in sorted(families.items()):
    rel, top = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
    print(f"  {family:16s} {len(rows):3d}  change min {rel.min():.4f} median {np.median(rel):.4f} max {rel.max():.4f}   rank-1 share min {top.min():.3f} median {np.median(top):.3f} max {top.max():.3f}")
sys.exit(1 if problems or unexpected or missing else 0)
