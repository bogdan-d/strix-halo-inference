# Weight profiles

The CLI and dashboard share `config/weights.json`. Every engine has a `default`; other keys are explicit choices such as Gufo's `lora` and Halogen's `abliterated-r2`. Halogen's validated lower-memory `abliterated-ht43` profile shares r2's companion directory but has a separate prompt cache; see [trial results](engine-updates.md#november-15-ht43-abliterated-trial). Halogen r2 carries its own MTP head and reuses pinned stock n-gram, tokenizer and vision companions through reflink copies. A profile selects model files and their manifest, not arbitrary launch flags. Image pins, GPU permissions, context, sampling and API model names remain engine settings.

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

- Gufo's `model` is the first GGUF shard and `mtp` is its matching draft head. Include every shard and the head in the manifest.
- Halogen's `model` is the checkpoint file. Its n-gram companion, `tokenizer/` and optional `qwen38-flash-next-vision.hgn` live beside it. Include the required companions in the manifest.
- Strixite's `model` is the complete model directory, including its n-gram table, tokenizer, MTP and vision files. Include the whole selected package in the manifest.

A manifest has tab-separated columns: SHA-256, byte size and destination path. By default destinations are relative to the model root. An optional profile `directory` prefixes them; the default profiles use their repository directory and existing manifests. Preserve the default profiles' directory and manifest mapping to the pins in `config/pins.env`.

For downloadable alternative profiles, add three columns to each row: source Hugging Face repository, immutable revision and source file path. This allows a local destination to differ from its upstream path. Pin all downloaded files, including shared companions, then use `bin/models.sh download ENGINE PROFILE`. Existing files are checked and never deliberately overwritten. Download sources without an explicit source-file column retain the NPU convention of dropping the destination's first path component; new profiles should supply the explicit sixth column.

Locally generated files have only the first three columns. A missing local file fails with “Provision this profile first”; the downloader cannot recreate a patch. Record its source revision, patch hashes and exact generation command in the update record, and hash the output into its manifest. Gufo’s abliterated profiles use the [Huihui v2 LoRA provisioning helper](#gufo-huihui-v2-lora-profiles).

Restart the dashboard helper after changing the catalog, and refresh the page. Missing or incomplete profiles stay visible but cannot be started. After provisioning, run full verification, health, a real generation and the engine's live lifecycle test before treating the profile as validated.

A profile does not add engine compatibility. In particular, Gufo 0.35.0's stock Flash-Next loader, unchanged from 0.34.0, does not support the smaller IQ quantizations: see [Gufo extensions](gufo-extensions.md) before adding them. The `iq4-xs` and `iq4-xs-lora` profiles declare `"extension": "flash_next_iq"`; they require the separately installed, image-specific native module before they become available. Ordinary Gufo profiles do not mount the extension store. See the extension guide for provisioning and validation status.

## Gufo Huihui v2 LoRA profiles

Gufo 0.35.0 loads GGUF checkpoints. The `lora` (UD-Q4_K_XL) and `iq4-xs-lora` profiles use the [2.3 MB Huihui v2 adapter](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA/tree/dee8e0177e4e61efdaa3fb7128c40d6ab7a085d4). Provisioning reflinks the four installed stock shards, merges the 96 rank-one updates offline, requantizes the edited tensors in their original formats, verifies the output hashes and shares all untouched extents with stock. It requires reflinks on the model filesystem and fails if cloning is unavailable. The two profiles have separate prompt caches. Switch by stopping and starting Gufo. Per-request switching requires native engine support.

Run the command for the desired installed stock quant. The helper downloads and verifies the pinned adapter if missing and refuses to overwrite an existing output directory. IQ4_XS uses llama.cpp’s reference Q6_K quantizer during provisioning and requires the existing Gufo IQ extension for inference. Building the quantizer dependency from source requires a C/C++ toolchain.

```bash
uv run bin/gufo-lora.py UD-Q4_K_XL
uv run --with llama-cpp-python==0.3.37 bin/gufo-lora.py UD-IQ4_XS

bin/run.sh gufo start --weights lora --wait
# For IQ4_XS, use --weights iq4-xs-lora instead.
```

On this Btrfs host the merged Q4_K_XL and IQ4_XS directories used 852.57 MiB and 810.98 MiB exclusively on November 18, versus 103.69 GiB and 87.24 GiB for the older fully materialized Huihui patch outputs. Use `btrfs filesystem du -s DIRECTORY` to distinguish exclusive and shared storage. A normal copy or backup to another filesystem may materialize all shards. The merged tensors approximate the original patch because the adapter was extracted from Q5 and both local formats requantize the update. The two original patched copies were deleted after validation and their profiles retired.

Both LoRA profiles passed Gufo 0.35.0 readiness, generation, conversation, tool calls (including streamed arguments), cancellation and generation after cancellation at native 262144 context with MTP on November 18. A numerical check sampled every 16th row across all 96 edited matrices and compared each edit against the existing Huihui patch relative to the same stock weights. Cosine similarity was 0.965 for Q4_K_XL and 0.900 for IQ4_XS.

On November 18, a paired Gufo IQ4_XS trial compared the original patch with the LoRA merge, each starting with a fresh prompt cache. Neither profile triggered an opening refusal marker on any of five fixed prompts at temperature zero with thinking off. Four replies had the usual 96-token limit. The paywall prompt was capped at eight tokens for both profiles, so only its opening was assessed. Both passed all four Pi 1.5.2 coding trials (env-parser and CSV-filter, thinking off and medium), including independent checks and the strict argument guard. The original patch took 100.1 seconds total with one intermediate bash error. The LoRA merge took 162.8 seconds with four intermediate bash errors, including two in the 67.9-second CSV-filter/off run. Each condition ran once.

The November 18 Q4_K_XL comparison used the same five refusal probes, reply limits, fresh caches and four Pi coding conditions. Both profiles had zero opening refusal markers, passed all four independent coding checks and strict argument checks, and recorded zero tool errors. Total coding time was 88.73 seconds for the original patch and 101.59 seconds for the LoRA merge. The merge finished three trials sooner, but CSV-filter with medium thinking took 53.59 seconds versus 26.11 seconds for the patch. Each condition ran once. Both shutdowns passed the memory-release gate.
