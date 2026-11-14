# 01: Update Gufo's weights to UD 3.1 UD-Q4_K_XL

**What to build:** Move Gufo's pinned weights from Unsloth's October export (`38bb39ee97821de2c9009abb7e93950eec396e66`) to the UD 3.1 `UD-Q4_K_XL`. Every tensor keeps its type and shape (header scan, November 15: 1,224 tensors, no mismatches), so loading and memory should not change; the quantised values are new. This is the only ticket that changes what the launcher serves by default.

**Blocked by:** None.

**Status:** ready-for-agent

Pin `GUFO_REVISION=d96201194f103c906994f283f504209dc8d2a10c`, the revision Gufo's docs and CI use. The four shards are byte-identical at Unsloth's `main` on November 15 (`f5d175de2cf7f720d45d6064019a81fcf056e986`).

| File | Bytes | SHA-256 |
|---|---|---|
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` | 10,946,618 | `acc44040f74d0e55fb89c3967056cce5dbda1bcc52e909c3ba6fc72b5e9c0858` |
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf` | 49,720,539,552 | `45792ae869072d8229384c51c7c73dd959e191505252b41dd71852d9746f5ce4` |
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf` | 32,803,030,176 | `8c76e79d444b16a663d9c8db54e585ed3b1da13eebd2619c37b0c355da803c82` |
| `UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf` | 28,800,138,432 | `5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36` |
| `MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` (unchanged, already on disk) | 2,786,568,256 | `5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6` |

The new shards have the same file names as the October ones, and `bin/models.sh` never overwrites an existing file. Rename the October directory first, for example to `UD-Q4_K_XL.october-38bb39ee/` beside it, and leave it there. Shard 4 now holds only the n-gram table and is shared with the other UD 3.1 quants (ticket 05 reuses it).

- [ ] No managed engine is running, and the October `UD-Q4_K_XL` directory is renamed, not deleted.
- [ ] `config/pins.env` and `config/gufo-files.tsv` carry the revision and the rows above, and `tests/models.sh` passes.
- [ ] `bin/models.sh download gufo` then `bin/models.sh verify gufo` succeed (111.3 GB).
- [ ] Trial checks 2 to 6 from the [spec](../spec.md#trial-checks) pass with `gufo`.
- [ ] The startup allocation is recorded against the 89.12 GiB measured on November 14, and decode speed against the October file on the same prompt.
- [ ] `docs/engine-updates.md` records the change, and every doc that names the October revision as current is updated (`grep -rn 38bb39ee README.md docs`).
- [ ] The user has decided whether the October shards are deleted or kept.

Rollback: restore the two config files and rename the directory back.

## Comments
