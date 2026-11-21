# Weight profiles

The CLI and dashboard share `config/weights.json`. Every engine has a `default`; other keys are explicit choices such as Gufo's `lora` and Halogen's `abliterated-r2`. Halogen's validated lower-memory `abliterated-ht43` profile shares r2's companion directory but has a separate prompt cache; see [trial results](engine-updates.md#november-15-ht43-abliterated-trial). Halogen r2 carries its own MTP head and reuses pinned stock n-gram, tokenizer and vision companions through reflink copies. A profile selects model files and their manifest, not arbitrary launch flags. The one exception to the image pins is a Gufo profile with an `adapter`, which runs the local fork image. Image pins, GPU permissions, context, sampling and API model names remain engine settings.

```bash
bin/run.sh gufo weights
bin/models.sh check gufo lora
bin/models.sh verify gufo lora
bin/run.sh gufo start --weights lora --wait
```

Stop the running engine before switching. `status` reports the actual weight path and profile label from the container. A profile's writable cache is `CACHE_ROOT/ENGINE/PROFILE`; model storage stays read-only at `/models`. Cache clearing removes all profiles' prompt state for the chosen engine, including older caches directly in the engine directory. Changing a profile's weights should use a new profile name if its engine cannot guarantee cache invalidation by weight identity.

## Register a checkpoint or quant

Add an entry under its engine in `config/weights.json`. Profile names use lowercase letters, digits and hyphens. Paths are relative to `/home/bogdan/models` (or `MODELS_DIR`); manifests are relative to `config/`.

```json
"trial-q4": {
  "label": "Trial Q4",
  "model": "publisher/model/quant/first-shard.gguf",
  "mtp": "publisher/model/MTP/matching-head.gguf",
  "manifest": "weights/gufo-trial-q4.tsv"
}
```

- Gufo's `model` is the first GGUF shard and `mtp` is its matching draft head. Include every shard and the head in the manifest. An optional `adapter` names a GGUF LoRA merged at load by the [local fork image](#lora-merged-at-load); include it in the manifest too.
- Halogen's `model` is the checkpoint file. Its n-gram companion, `tokenizer/` and optional `qwen38-flash-next-vision.hgn` live beside it. Include the required companions in the manifest.
- Strixite's `model` is the complete model directory, including its n-gram table, tokenizer, MTP and vision files. Include the whole selected package in the manifest.

A manifest has tab-separated columns: SHA-256, byte size and destination path. By default destinations are relative to the model root. An optional profile `directory` prefixes them; the default profiles use their repository directory and existing manifests. Preserve the default profiles' directory and manifest mapping to the pins in `config/pins.env`.

For downloadable alternative profiles, add three columns to each row: source Hugging Face repository, immutable revision and source file path. This allows a local destination to differ from its upstream path. Pin all downloaded files, including shared companions, then use `bin/models.sh download ENGINE PROFILE`. Existing files are checked and never deliberately overwritten. Download sources without an explicit source-file column retain the NPU convention of dropping the destination's first path component; new profiles should supply the explicit sixth column.

Locally generated files have only the first three columns. A missing local file fails with “Provision this profile first”; the downloader cannot recreate a patch. Record its source revision, patch hashes and exact generation command in the update record, and hash the output into its manifest. Gufo’s `iq4-xs-lora` profile uses the [Huihui v2 LoRA provisioning helper](#iq4-xs-lora-reflinked-merge).

Restart the dashboard helper after changing the catalog, and refresh the page. Missing or incomplete profiles stay visible but cannot be started. After provisioning, run full verification, health, a real generation and the engine's live lifecycle test before treating the profile as validated.

A profile does not add engine compatibility. In particular, Gufo 0.35.0's stock Flash-Next loader, unchanged from 0.34.0, does not support the smaller IQ quantizations: see [Gufo extensions](gufo-extensions.md) before adding them. The `iq4-xs` and `iq4-xs-lora` profiles declare `"extension": "flash_next_iq"`; they require the separately installed, image-specific native module before they become available. Ordinary Gufo profiles do not mount the extension store. See the extension guide for provisioning and validation status.

## Gufo Huihui v2 LoRA profiles

The `lora` (UD-Q4_K_XL) and `iq4-xs-lora` profiles apply the [2.3 MB Huihui v2 adapter](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA/tree/dee8e0177e4e61efdaa3fb7128c40d6ab7a085d4), a llama.cpp GGUF LoRA with 96 rank-one updates. `lora` merges it while the stock weights load. `iq4-xs-lora` still serves a merged copy made in advance. The two profiles have separate prompt caches. Switch by stopping and starting Gufo. One adapter applies to every request; per-request switching is not implemented.

### `lora`: merged at load

The profile's `adapter` key names the adapter file. Its manifest lists the four stock UD-Q4_K_XL shards, the shared MTP head and the adapter, each with a pinned source, so `bin/models.sh download gufo lora` provisions it and nothing is merged on disk. For a profile with an `adapter`, the launcher runs the local fork image `GUFO_FORK_IMAGE` instead of `GUFO_IMAGE` and adds `--lora /models/ADAPTER`.

Stock Gufo 0.35.0 cannot load an adapter for this model ([feature request](https://github.com/gufo-org/gufo/issues/1247)). The fork adds it for the built-in UD-Q4_K_XL provider: each target tensor is dequantized, the update is added in float32 and the result is stored as Q8_0 again, so speed and memory match the stock model. The MTP head stays stock. The disk prompt cache is keyed by the adapter's SHA-256 and scale, so stock and adapter state never mix.

Build the image once, and again after changing `GUFO_FORK_REVISION`:

```bash
bin/gufo-fork.sh
bin/run.sh gufo start --weights lora --wait
```

- **Source:** the fork checkout at `../gufo`, or `GUFO_FORK_SOURCE`. The script builds the committed tree at `GUFO_FORK_REVISION`, never the working copy. That commit is on the local branch `feat/flash-next-lora` and is not pushed.
- **Image definition:** [gufo-org/toolboxes](https://github.com/gufo-org/toolboxes) at `GUFO_FORK_TOOLBOXES_REVISION`, the definition behind `GUFO_IMAGE`, with the engine input replaced by the fork. User, layout and extension SDK therefore match the upstream runtime image.
- **Build container:** the pinned `GUFO_FORK_NIX_IMAGE`, rootless, with network access. Nix runs without its sandbox there and accepts the fork flake's binary caches, `cache.nixos.org` and `gufo.cachix.org`. The toolchain is kept in the Podman volume `gufo-build-nix` (8.4 GiB on November 21), or `GUFO_FORK_NIX_VOLUME`.
- **Result:** `localhost/strix-halo-inference/gufo-fork`, tagged with the short revision. The script checks the image's engine-revision label and its digest against `GUFO_FORK_IMAGE`, and prints the reference to pin when they differ. With the toolchain cached, the build took about three minutes on November 21.
- **Updates:** `bin/update.py` moves only the upstream pins. The fork image keeps its own engine version until the fork is rebased and rebuilt.

On November 21 the fork image (Gufo 0.35.0 at `452c7c0`, digest in `config/pins.env`) passed `bin/models.sh verify gufo lora`, native-262144 readiness with MTP, the smoke request, and `tests/live.py`: conversation recall, named and streamed tool calls (four argument fragments), disconnect slot release and generation after cancellation. The startup log reported 96 tensors merged in 0.91 s and 84,935 MiB of GPU allocation; readiness took 62 s with the disk cache enabled. One 340-token prose reply decoded at 39.9 tokens/s with 180 of 315 drafts accepted. After stopping, kernel GTT use returned to 1.6 GiB. These are single exploratory samples.

Before wiring, the loader's output was compared with the merged copy this profile served until November 21: all 96 target tensors, 885,719,040 bytes, with no differing byte. With the same binary at temperature zero, three prompts gave identical text from the stock weights plus adapter and from the merged copy. The November 18 results below were measured on that merged copy and carry over to the same weights; they were not repeated on the fork image.

### `iq4-xs-lora`: reflinked merge

Provisioning reflinks the four installed stock UD-IQ4_XS shards, merges the 96 updates offline, requantizes the edited tensors in their original formats, verifies the output hashes and shares all untouched extents with stock. It requires reflinks on the model filesystem and fails if cloning is unavailable. The helper downloads and verifies the pinned adapter if missing and refuses to overwrite an existing output directory. It uses llama.cpp’s reference Q6_K quantizer and requires the existing Gufo IQ extension for inference. Building the quantizer dependency from source requires a C/C++ toolchain.

```bash
uv run --with llama-cpp-python==0.3.37 bin/gufo-lora.py UD-IQ4_XS
bin/run.sh gufo start --weights iq4-xs-lora --wait
```

On this Btrfs host the merged IQ4_XS directory used 810.98 MiB exclusively on November 18, and the Q4_K_XL merged copy that `lora` served until November 21, deleted that day, used 852.57 MiB, versus 103.69 GiB and 87.24 GiB for the older fully materialized Huihui patch outputs. Use `btrfs filesystem du -s DIRECTORY` to distinguish exclusive and shared storage. A normal copy or backup to another filesystem may materialize all shards. The merged tensors approximate the original patch because the adapter was extracted from Q5 and both local formats requantize the update. The two original patched copies were deleted after validation and their profiles retired.

### November 18 results on the merged copies

Both merged copies passed Gufo 0.35.0 readiness, generation, conversation, tool calls (including streamed arguments), cancellation and generation after cancellation at native 262144 context with MTP on November 18. A numerical check sampled every 16th row across all 96 edited matrices and compared each edit against the existing Huihui patch relative to the same stock weights. Cosine similarity was 0.965 for Q4_K_XL and 0.900 for IQ4_XS.

On November 18, a paired Gufo IQ4_XS trial compared the original patch with the LoRA merge, each starting with a fresh prompt cache. Neither profile triggered an opening refusal marker on any of five fixed prompts at temperature zero with thinking off. Four replies had the usual 96-token limit. The paywall prompt was capped at eight tokens for both profiles, so only its opening was assessed. Both passed all four Pi 1.5.2 coding trials (env-parser and CSV-filter, thinking off and medium), including independent checks and the strict argument guard. The original patch took 100.1 seconds total with one intermediate bash error. The LoRA merge took 162.8 seconds with four intermediate bash errors, including two in the 67.9-second CSV-filter/off run. Each condition ran once.

The November 18 Q4_K_XL comparison used the same five refusal probes, reply limits, fresh caches and four Pi coding conditions. Both profiles had zero opening refusal markers, passed all four independent coding checks and strict argument checks, and recorded zero tool errors. Total coding time was 88.73 seconds for the original patch and 101.59 seconds for the LoRA merge. The merge finished three trials sooner, but CSV-filter with medium thinking took 53.59 seconds versus 26.11 seconds for the patch. Each condition ran once. Both shutdowns passed the memory-release gate.
