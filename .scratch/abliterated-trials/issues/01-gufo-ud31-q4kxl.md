# 01: Update Gufo's weights to UD 3.1 UD-Q4_K_XL

**What to build:** Move Gufo's pinned weights from Unsloth's October export (`38bb39ee97821de2c9009abb7e93950eec396e66`) to the UD 3.1 `UD-Q4_K_XL`. Every tensor keeps its type and shape (header scan, November 15: 1,224 tensors, no mismatches), so loading and memory should not change; the quantised values are new. This is the only ticket that changes what the launcher serves by default.

**Blocked by:** None.

**Status:** resolved

Pin `GUFO_REVISION=d96201194f103c906994f283f504209dc8d2a10c`, the revision Gufo's docs and CI use. The four shards are byte-identical at Unsloth's `main` on November 15 (`f5d175de2cf7f720d45d6064019a81fcf056e986`).

| File | Bytes | SHA-256 |
|---|---|---|
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` | 10,946,618 | `acc44040f74d0e55fb89c3967056cce5dbda1bcc52e909c3ba6fc72b5e9c0858` |
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf` | 49,720,539,552 | `45792ae869072d8229384c51c7c73dd959e191505252b41dd71852d9746f5ce4` |
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf` | 32,803,030,176 | `8c76e79d444b16a663d9c8db54e585ed3b1da13eebd2619c37b0c355da803c82` |
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf` | 28,800,138,432 | `5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36` |
| `MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` (unchanged, already on disk) | 2,786,568,256 | `5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6` |

The new shards have the same file names as the October ones, and `bin/models.sh` never overwrites an existing file. Rename the October directory first, for example to `UD-Q4_K_XL.october-38bb39ee/` beside it, and leave it there. Shard 4 now holds only the n-gram table and is shared with the other UD 3.1 quants (ticket 05 reuses it).

- [x] No managed engine is running, and the October `UD-Q4_K_XL` directory is renamed, not deleted.
- [x] `config/pins.env` and `config/gufo-files.tsv` carry the revision and the rows above, and `tests/models.sh` passes.
- [x] `bin/models.sh download gufo` then `bin/models.sh verify gufo` succeed (111.3 GB).
- [x] Trial checks 2 to 6 from the [spec](../spec.md#trial-checks) pass with `gufo`.
- [x] The startup allocation is recorded against the 89.12 GiB measured on November 14, and decode speed against the October file on the same prompt.
- [x] `docs/engine-updates.md` records the change, and every doc that names the October revision as current is updated (`grep -rn 38bb39ee README.md docs`).
- [x] The huihui patch from ticket 04 is re-applied to the UD 3.1 shards (no download, under a minute), checked with `verify_patch.py` and `probe.py gufo`, and recorded. The copy patched from the October file is then superseded.
- [x] The user has decided whether the October shards, and the copy patched from them (111 GB), are deleted or kept.

Rollback after the user-requested cleanup requires restoring the October pin/manifest and downloading that revision again; no October weight copy remains.

## Comments

- November 15, in progress: upstream revision and all five hashes rechecked against Hugging Face and Gufo v0.34.0's current model guide. Download started after moving the October directory aside with no engines active. User also requested shared CLI/dashboard profiles for per-engine weight selection, including future lower quants. User then explicitly requested deleting both October copies; they will be removed after UD 3.1 stock and patched validation.

- Completed November 15: both UD 3.1 profiles passed hash/layout, native-256K MTP readiness/generation, live conversation/tools/cancellation, exact identifiers and comparison probes. Both retain 89.12 GiB startup allocation. The stock model refused all five probes; the patched model answered all five. Both October directories were deleted as requested after validation, and all engines were stopped. Shared named profiles, download manifests, isolated profile caches, dashboard selectors, tests and docs are implemented. Full results and limitations are in `docs/engine-updates.md` (UD 3.1 update).
