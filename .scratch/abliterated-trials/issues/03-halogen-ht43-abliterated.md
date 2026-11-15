# 03: Halogen with the HT43 abliterated checkpoint

**What to build:** Test the smaller abliterated checkpoint from the same repository as r2. It applies the same abliteration to peonist's HT43 checkpoint, which peonist says holds about 8 GiB less in memory than v2. It has passed only offline weight checks and has never been run on a GPU, so this is the first real test of it.

**Blocked by:** 02 (launcher override, trial manifest, and the r2 results to compare with).

**Status:** resolved

Source: [Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated](https://huggingface.co/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated) at revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`. The HT43 file on `main` differs (57,618,253,792 bytes, `e74a0d27…`) while the card still lists the hash below, so pin the revision.

| File | Bytes | SHA-256 |
|---|---|---|
| `qwen38-flash-next-ht43-abliterated.hgn` | 57,618,253,824 | `2beaad7b6d5107d7abfa866b33b47287160a68b9fc45b86020dbaa884955329c` |

It goes in the r2 directory and uses the same companion files.

- [x] The file is downloaded and its size and SHA-256 verified (57.6 GB).
- [x] Halogen's `verify` and `inspect` pass on it under 0.20.4.
- [x] `ppl` is recorded against both stock v2 and r2 on the same corpus as ticket 02.
- [x] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `halogen`.
- [x] Startup allocation, `MemAvailable` and decode speed are recorded against r2 and stock v2.
- [x] The record states which of r2 and HT43 is the better abliterated Halogen checkpoint for this host, and `docs/abliterated-models.md` is updated.

The stock HT43 checkpoint is not on disk. Without it, a perplexity gap to r2 cannot be split between HT43 itself and the abliteration; download peonist's `qwen38-flash-next-ht43.hgn` (57.6 GB) only if that question matters.

## Comments

- November 15: ticket 01 also supplies shared CLI/dashboard weight profiles and alternative download manifests at the user's request. Register this trial in `config/weights.json` and follow `docs/weight-profiles.md`; model and Gufo MTP selection now come from the profile. Extension installation/loading still needs its own implementation and validation.

- Started November 15 after commit `dc820fc` (r2 trial and dashboard layout). Rechecked pinned HT43 size/hash against Hugging Face metadata; registered `abliterated-ht43` beside r2, sharing its already-verified companion files. The full ticket 02 WikiText-2 corpus and stock reference will be reused.

- Provisioning complete: all nine file hashes passed. Native 0.20.4 `verify` reports PASS for 2,015 tensors, 53.66 GiB, v2, model ID `qwen3.8-flash-next-ht43`; header, table, layout, payload sizes, checksums, codebooks and scales OK, geometry checked on 1,197 tensors (818 with no rule). `inspect --no-hash --json` succeeded. HT43 does not exhibit r2's table-order verifier error.

- Completed November 15: both full-corpus comparisons passed, followed by live conversation/tools/cancellation, five exact identifiers and five refusal probes. Prefer `abliterated-ht43` on this host for its 70.2 GiB total allocation and passing quality/behavior checks; retain r2 for comparison. [Full results and limits](../../../docs/engine-updates.md#november-15-ht43-abliterated-trial) record the host-memory warning and untested workloads. The helper was reloaded to expose the profile; no inference container remains running. Stock HT43 was not downloaded.
