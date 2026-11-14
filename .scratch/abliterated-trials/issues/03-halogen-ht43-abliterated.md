# 03: Halogen with the HT43 abliterated checkpoint

**What to build:** Test the smaller abliterated checkpoint from the same repository as r2. It applies the same abliteration to peonist's HT43 checkpoint, which peonist says holds about 8 GiB less in memory than v2. It has passed only offline weight checks and has never been run on a GPU, so this is the first real test of it.

**Blocked by:** 02 (launcher override, trial manifest, and the r2 results to compare with).

**Status:** ready-for-agent

Source: [Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated](https://huggingface.co/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated) at revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`. The HT43 file on `main` differs (57,618,253,792 bytes, `e74a0d27…`) while the card still lists the hash below, so pin the revision.

| File | Bytes | SHA-256 |
|---|---|---|
| `qwen38-flash-next-ht43-abliterated.hgn` | 57,618,253,824 | `2beaad7b6d5107d7abfa866b33b47287160a68b9fc45b86020dbaa884955329c` |

It goes in the r2 directory and uses the same companion files.

- [ ] The file is downloaded and its size and SHA-256 verified (57.6 GB).
- [ ] Halogen's `verify` and `inspect` pass on it under 0.20.4.
- [ ] `ppl` is recorded against both stock v2 and r2 on the same corpus as ticket 02.
- [ ] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `halogen`.
- [ ] Startup allocation, `MemAvailable` and decode speed are recorded against r2 and stock v2.
- [ ] The record states which of r2 and HT43 is the better abliterated Halogen checkpoint for this host, and `docs/abliterated-models.md` is updated.

The stock HT43 checkpoint is not on disk. Without it, a perplexity gap to r2 cannot be split between HT43 itself and the abliteration; download peonist's `qwen38-flash-next-ht43.hgn` (57.6 GB) only if that question matters.

## Comments
