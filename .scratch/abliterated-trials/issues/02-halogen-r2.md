# 02: Halogen with Quat3rnion r2

**What to build:** Download the r2 abliterated checkpoint and test it under Halogen 0.20.4. r2 is peonist's stock v2 checkpoint with 149 tensors replaced by orcarouter's abliteration. Its author tested it on Halogen 0.15.0 only. This ticket also adds the trial manifest support and the Halogen checkpoint override described in the [spec](../spec.md#launcher-and-manifest-changes).

**Blocked by:** None.

**Status:** ready-for-agent

Source: [Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated](https://huggingface.co/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated) at revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`. The file of the same name on `main` is a different, never-run conversion; do not use it.

| File | Bytes | SHA-256 |
|---|---|---|
| `qwen38-flash-next-v2-abliterated.hgn` | 88,737,777,792 | `7bbac319851b500639462133085156b4f998dec562f511e65ca1c14d7af5163e` |

Put it in `/home/bogdan/models/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated/` with reflink copies of the stock `qwen38-flash-next-ngram.hgn`, `qwen38-flash-next-vision.hgn` and `tokenizer/` from the peonist directory. r2 was built against companion files whose hashes match the pinned ones.

- [ ] `bin/models.sh` handles a trial manifest and `bin/run.sh halogen` takes an explicit checkpoint override; the stock default is unchanged, the README documents both, and the offline tests pass.
- [ ] The file is downloaded and its size and SHA-256 verified (88.7 GB).
- [ ] Halogen's `verify` and `inspect` run on r2, with their output lines recorded. r2 keeps 22 GB of replaced payloads unreferenced, so note anything `verify` says about them.
- [ ] `ppl` compares r2 with the stock v2 checkpoint on the WikiText-2 raw test split ([checkpoint tools](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/checkpoint-tools.md); corpus kept outside the repository). The card reports perplexity 3.134 against 3.144, KL 0.060 and 92.2% top-token agreement on 0.15.0.
- [ ] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `halogen`, with the stock checkpoint as the control for the refusal probe.
- [ ] Startup allocation and decode speed are recorded against stock v2 (the card claims the same 62.1 GiB of weights and the same speed).
- [ ] Results are recorded in `docs/engine-updates.md`, and the r2 status in `docs/abliterated-models.md` is updated from "author-tested on 0.15.0 only".

## Comments
