# Weight profiles

The CLI and dashboard share `config/weights.json`. Every engine has a `default`; other keys are explicit choices such as Gufo's `lora` and Halogen's `abliterated-r2`. Halogen's validated lower-memory `abliterated-ht43` profile shares r2's companion directory but has a separate prompt cache; see [trial results](engine-updates.md#november-15-ht43-abliterated-trial). Halogen r2 carries its own MTP head and reuses pinned stock n-gram, tokenizer and vision companions through reflink copies. A profile selects model files and their manifest, not arbitrary launch flags. The one exception to the image pins is a Gufo profile with an `adapter` and no `extension`, which runs the local fork image. Gufo profiles can select their served model ID, context limit and drafting method.

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

- Gufo's `model` is the target GGUF or its first shard. Set `mtp` for a Flash-Next MTP head or `dflash` for a 27B DFlash2 drafter. Include all target files and the selected drafter in the manifest. The optional `served_model` and `context` select the API model ID and the default and maximum context in tokens. An optional `adapter` names a GGUF LoRA merged at load, by the IQ extension when the profile also names an `extension` and otherwise by the [local fork image](#lora-merged-at-load); include it in the manifest too.
- Halogen's `model` is the checkpoint file. Its n-gram companion, `tokenizer/` and optional `qwen38-flash-next-vision.hgn` live beside it. Include the required companions in the manifest.
- Strixite's `model` is the complete model directory, including its n-gram table, tokenizer, MTP and vision files. Include the whole selected package in the manifest.

A manifest has tab-separated columns: SHA-256, byte size and destination path. By default destinations are relative to the model root. An optional profile `directory` prefixes them; the default profiles use their repository directory and existing manifests. Preserve the default profiles' directory and manifest mapping to the pins in `config/pins.env`.

For downloadable alternative profiles, add three columns to each row: source Hugging Face repository, immutable revision and source file path. This allows a local destination to differ from its upstream path. Pin all downloaded files, including shared companions, then use `bin/models.sh download ENGINE PROFILE`. Existing files are checked and never deliberately overwritten. Download sources without an explicit source-file column retain the NPU convention of dropping the destination's first path component; new profiles should supply the explicit sixth column.

Locally generated files have only the first three columns. A missing local file fails with “Provision this profile first”; the downloader cannot recreate a patch. Record its source revision, patch hashes and exact generation command in the update record, and hash the output into its manifest.

Restart the dashboard helper after changing the catalog, and refresh the page. Missing or incomplete profiles stay visible but cannot be started. After provisioning, run full verification, health, a real generation and the engine's live lifecycle test before treating the profile as validated.

A profile does not add engine compatibility. In particular, Gufo 0.35.0's stock Flash-Next loader, unchanged from 0.34.0, does not support the smaller IQ quantizations: see [Gufo extensions](gufo-extensions.md) before adding them. The `iq4-xs` and `iq4-xs-lora` profiles declare `"extension": "flash_next_iq"`; they require the separately installed, image-specific native module before they become available. Ordinary Gufo profiles do not mount the extension store. See the extension guide for provisioning and validation status.

## Gufo Qwen3.8 27B

Select `27b-heretic` in the dashboard or start it from the CLI. It serves `qwen3.8-27b` with one session and 131,072 tokens of context. Its [manifest](../config/weights/gufo-27b-heretic.tsv) pins the UD-Q4_K_XL target, Q4_K_M DFlash2 drafter and Heretic GGUF adapter (17.52 GiB total). The fork image merges the adapter during load. Use `SPECULATIVE=off` for autoregressive decoding or `CONTEXT=32768` for a smaller window. This profile accepts text input.

```bash
bin/gufo-fork.sh
bin/models.sh download gufo 27b-heretic
bin/run.sh gufo start --weights 27b-heretic --wait
pi --provider gufo --model qwen3.8-27b --thinking xhigh
```

## Gufo Huihui v2 LoRA profiles

The `lora` (UD-Q4_K_XL) and `iq4-xs-lora` profiles apply the [2.3 MB Huihui v2 adapter](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA/tree/dee8e0177e4e61efdaa3fb7128c40d6ab7a085d4), a llama.cpp GGUF LoRA with 96 rank-one updates. Both merge it while the stock weights load, so neither needs a merged copy of the checkpoint. The two profiles have separate prompt caches. Switch by stopping and starting Gufo. One adapter applies to every request; per-request switching is not implemented.

### `lora`: merged at load

The profile's `adapter` key names the adapter file. Its manifest lists the four stock UD-Q4_K_XL shards, the shared MTP head and the adapter, each with a pinned source, so `bin/models.sh download gufo lora` provisions it and nothing is merged on disk. For a profile with an `adapter` and no `extension`, the launcher runs the local fork image `GUFO_FORK_IMAGE` instead of `GUFO_IMAGE`. Every adapter profile gets `--lora /models/ADAPTER`.

Stock Gufo 0.35.0 cannot load an adapter for this model ([feature request](https://github.com/gufo-org/gufo/issues/1247)). The fork adds it for the built-in UD-Q4_K_XL provider: each target tensor is dequantized, the update is added in float32 and the result is stored as Q8_0 again, so speed and memory match the stock model. The MTP head stays stock. The disk prompt cache is keyed by the adapter's SHA-256 and scale, so stock and adapter state never mix.

Build the image once, and again after changing `GUFO_FORK_REVISION`:

```bash
bin/gufo-fork.sh
bin/run.sh gufo start --weights lora --wait
```

- **Source:** the fork checkout at `../gufo`, or `GUFO_FORK_SOURCE`. The script builds the committed tree at `GUFO_FORK_REVISION`, never the working copy. That commit is on branch `feat/qwen27-lora` of [bogdan-d/gufo](https://github.com/bogdan-d/gufo/tree/feat/qwen27-lora).
- **Image definition:** [gufo-org/toolboxes](https://github.com/gufo-org/toolboxes) at `GUFO_FORK_TOOLBOXES_REVISION`, the definition behind `GUFO_IMAGE`, with the engine input replaced by the fork. User, layout and extension SDK therefore match the upstream runtime image.
- **Build container:** the pinned `GUFO_FORK_NIX_IMAGE`, rootless, with network access. Nix runs without its sandbox there and accepts the fork flake's binary caches, `cache.nixos.org` and `gufo.cachix.org`. The toolchain is kept in the Podman volume `gufo-build-nix` (8.4 GiB on November 21), or `GUFO_FORK_NIX_VOLUME`.
- **Result:** `localhost/strix-halo-inference/gufo-fork`, tagged with the short revision. The script checks the image's engine-revision label and its digest against `GUFO_FORK_IMAGE`, and prints the reference to pin when they differ. With the toolchain cached, the build took about three minutes on November 21.
- **Updates:** `bin/update.py` moves only the upstream pins. The fork image keeps its own engine version until the fork is rebased and rebuilt.

On November 21 the fork image (Gufo 0.35.0 at `452c7c0`, digest in `config/pins.env`) passed `bin/models.sh verify gufo lora`, native-262144 readiness with MTP, the smoke request, and `tests/live.py`: conversation recall, named and streamed tool calls (four argument fragments), disconnect slot release and generation after cancellation. The startup log reported 96 tensors merged in 0.91 s and 84,935 MiB of GPU allocation; readiness took 62 s with the disk cache enabled. One 340-token prose reply decoded at 39.9 tokens/s with 180 of 315 drafts accepted. After stopping, kernel GTT use returned to 1.6 GiB. These are single exploratory samples. On November 22 the image was rebuilt at `d77c890`, which adds [the release of the pages a merge reads](engine-updates.md#november-22-gufo-lora-loaders-release-the-pages-they-read), and passed the same checks.

Before wiring, the loader's output was compared with the merged copy this profile served until November 21: all 96 target tensors, 885,719,040 bytes, with no differing byte. With the same binary at temperature zero, three prompts gave identical text from the stock weights plus adapter and from the merged copy. The November 18 results below were measured on that merged copy and carry over to the same weights; they were not repeated on the fork image.

### `iq4-xs-lora`: merged at load by the IQ extension

The profile names the stock UD-IQ4_XS shards, the shared MTP head, the adapter and `"extension": "flash_next_iq"`. Both IQ profiles load the module at `GUFO_IQ_REVISION` into the pinned upstream image. The fork's [pinned revision](https://github.com/bogdan-d/flash-next-iq-gufo-extension/commit/5e262be42bc51202610899bfe32c22aad4b573b7) includes load-time adapter merging, the [release of the pages a merge reads](engine-updates.md#november-22-gufo-lora-loaders-release-the-pages-they-read), and the [short-prefill cache replay fix](gufo-extensions.md#iq4_xs-profiles-on-this-host). After installing the module, start the adapter profile with the commands below.

```bash
bin/models.sh download gufo iq4-xs-lora
bin/run.sh gufo start --weights iq4-xs-lora --wait
```

Every merged tensor is stored as Q8_0. In UD-IQ4_XS that leaves the 84 `ssm_out` and `ffn_down_shexp` targets in their stock format and turns the 12 Q6_K `attn_output` tensors into Q8_0 tensors of the same shape, 43.6 MiB more device memory in total. The cache identity and MTP behavior are the same as for `lora`.

Compared on November 21 with the merged copy this profile served until then, which re-encoded those 12 tensors as Q6_K: the 84 Q8_0 targets match byte for byte (685,178,880 bytes), and for the 12 converted tensors the error against the exact float32 merge is 1.2e-4 RMS, against 3.0e-4 for the merged copy, with every value inside Q8_0's rounding bound. On one tensor, `blk.23.attn_output`, the largest single error is higher than the merged copy's (5.4e-3 against 4.6e-3). The weights therefore differ slightly from the copy the November 18 results below were measured on, and greedy text diverged from it after 9 to 439 characters on three prompts.

On November 21 the profile passed `bin/models.sh verify gufo iq4-xs-lora`, native-262144 readiness with MTP, the smoke request and `tests/live.py` (conversation recall, named and streamed tool calls, disconnect slot release, generation after cancellation). The startup log reported 96 tensors merged in 0.88 s and 74,405 MiB of GPU allocation, 24 MiB above stock `iq4-xs` on the same module, which passed the same checks. One 345-token prose reply decoded at 52.3 tokens/s with 212 of 323 drafts accepted. At 32768 context without MTP the extension's own tests measured prefill and decode within 2% of stock and load time within 0.4 s, and the adapter build answered a prompt stock refused. The November 18 refusal probes and Pi coding trials were not repeated. More than one session was not tested. These are single exploratory samples. On November 22 both IQ profiles passed the same checks on the module at `d7794c4`.

The merged IQ4_XS directory `nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA/UD-IQ4_XS-d9620119`, 810.98 MiB exclusive on this Btrfs host, is no longer used by any profile. It stays on disk as the comparison reference for the extension's `tests/lora_oracle.cpp`. The offline merge script `bin/gufo-lora.py` was removed; commit `55a47e5` has it.

### November 18 results on the merged copies

Both merged copies passed Gufo 0.35.0 readiness, generation, conversation, tool calls (including streamed arguments), cancellation and generation after cancellation at native 262144 context with MTP on November 18. A numerical check sampled every 16th row across all 96 edited matrices and compared each edit against the existing Huihui patch relative to the same stock weights. Cosine similarity was 0.965 for Q4_K_XL and 0.900 for IQ4_XS.

On November 18, a paired Gufo IQ4_XS trial compared the original patch with the LoRA merge, each starting with a fresh prompt cache. Neither profile triggered an opening refusal marker on any of five fixed prompts at temperature zero with thinking off. Four replies had the usual 96-token limit. The paywall prompt was capped at eight tokens for both profiles, so only its opening was assessed. Both passed all four Pi 1.5.2 coding trials (env-parser and CSV-filter, thinking off and medium), including independent checks and the strict argument guard. The original patch took 100.1 seconds total with one intermediate bash error. The LoRA merge took 162.8 seconds with four intermediate bash errors, including two in the 67.9-second CSV-filter/off run. Each condition ran once.

The November 18 Q4_K_XL comparison used the same five refusal probes, reply limits, fresh caches and four Pi coding conditions. Both profiles had zero opening refusal markers, passed all four independent coding checks and strict argument checks, and recorded zero tool errors. Total coding time was 88.73 seconds for the original patch and 101.59 seconds for the LoRA merge. The merge finished three trials sooner, but CSV-filter with medium thinking took 53.59 seconds versus 26.11 seconds for the patch. Each condition ran once. Both shutdowns passed the memory-release gate.
