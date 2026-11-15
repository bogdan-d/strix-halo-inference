# 06: Strixite with ngkzngkz's abliterated weights

**What to build:** Test the only abliterated strixw build under Strixite 0.7.0, trying the n-gram table already on disk before downloading another 51.8 GB one. The weights are orcarouter's abliteration converted with Strixite v0.2.4. Nobody has published a run.

**Blocked by:** None.

**Status:** ready-for-agent

Source: [ngkzngkz/Qwen3.8-Flash-Next-Uncensored-strixw](https://huggingface.co/ngkzngkz/Qwen3.8-Flash-Next-Uncensored-strixw) at revision `b4b5a89317192fba5f09338e1ce954659e1aba6e`.

| File | Bytes | SHA-256 |
|---|---|---|
| `converted/Qwen3.8-Flash-Next.U-gdn_in-g128/weights.strixw` | 70,714,568,704 | `80622a7fa3b7bea816ff10ca9878a8d01f7ccaa8b3a4f8dbfc095dca77420893` |
| `converted/Qwen3.8-Flash-Next.U-gdn_in-g128/vision.strixw` | 898,331,648 | `585b32776286110b13037d8025ab72bad8aff0268531b2d85192a0fae70947e2` |
| `Qwen3.8-Flash-Next/tokenizer.json` | 12,809,320 | `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3` |
| `Qwen3.8-Flash-Next/config.json`, `generation_config.json`, `preprocessor_config.json`, `LICENSE` | 4,745; 202; 390; 3,235 | record after download |
| `converted/Qwen3.8-Flash-Next.ngram-q8/ngram.table` (only if the local table is rejected) | 51,840,252,928 | `3ece8dcf599965c20080462c764381dc26068a8aef5222e695b6232bb1f80fc8` |

What is known: the weights file declares strixw format version 4 and Strixite 0.7.0 reads versions 1 to 4, so the format gate should pass. The n-gram table differs from the pinned `wemoh` table on disk by SHA-256, but the headers differ only in the converter commit and six of seven sampled 1 MiB ranges are byte-identical; only the last range, at the end of the file, differs. The abliteration does not touch the table. Whether Strixite ties a table to its weights file is unknown.

First attempt: a new model directory with the downloaded files plus a reflink copy of the `wemoh` `ngram.table` in the same relative path.

- [ ] The weights, vision and small files are downloaded and verified (71.6 GB).
- [ ] `bin/run.sh strixite` takes an explicit model directory override; the stock default is unchanged, the README documents it, and the offline tests pass.
- [ ] Strixite starts with the local n-gram table, or its refusal message is recorded verbatim.
- [ ] If it refused, ngkzngkz's table is downloaded and verified (51.8 GB) and the start repeated.
- [ ] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `strixite`, with the stock `wemoh` package as the control for the refusal probe.
- [ ] Startup allocation and decode speed are recorded against the stock package.
- [ ] The record says which table was used. If the local one was accepted, it also says that equality with ngkzngkz's table was sampled, not proven.
- [ ] Results go in `docs/engine-updates.md` and `docs/abliterated-models.md`.

Strixite rejects named-tool selection and `required`, so check 8 uses `tool_choice: auto`, as `tests/strixite_live.py` does.

## Comments

- November 15: ticket 01 also supplies shared CLI/dashboard weight profiles and alternative download manifests at the user's request. Register this trial in `config/weights.json` and follow `docs/weight-profiles.md`; model and Gufo MTP selection now come from the profile. Extension installation/loading still needs its own implementation and validation.
