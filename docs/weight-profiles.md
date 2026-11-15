# Weight profiles

The CLI and dashboard share `config/weights.json`. Every engine has a `default`; other keys are explicit choices such as Gufo's `abliterated` and Halogen's `abliterated-r2`. Halogen's validated lower-memory `abliterated-ht43` profile shares r2's companion directory but has a separate prompt cache; see [trial results](engine-updates.md#november-15-ht43-abliterated-trial). Halogen r2 carries its own MTP head and reuses pinned stock n-gram, tokenizer and vision companions through reflink copies. A profile selects model files and their manifest, not arbitrary launch flags. Image pins, GPU permissions, context, sampling and API model names remain engine settings.

```bash
bin/run.sh gufo weights
bin/models.sh check gufo abliterated
bin/models.sh verify gufo abliterated
bin/run.sh gufo start --weights abliterated --wait
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

Locally generated files have only the first three columns. A missing local file fails with “Provision this profile first”; the downloader cannot recreate a patch. Record its source revision, patch hashes and exact generation command in the update record, and hash the output into its manifest. Gufo's current abliterated profile uses huihui's patch on the UD 3.1 export, not on the superseded October export.

Restart the dashboard helper after changing the catalog, and refresh the page. Missing or incomplete profiles stay visible but cannot be started. After provisioning, run full verification, health, a real generation and the engine's live lifecycle test before treating the profile as validated.

A profile does not add engine compatibility. In particular, Gufo 0.34.0's stock Flash-Next loader does not support the smaller IQ quantizations: see [Gufo extensions](gufo-extensions.md) before adding them. Extension installation and engine-specific flags need a separately validated launcher change.
