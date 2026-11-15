# 02: Halogen with Quat3rnion r2

**What to build:** Download the r2 abliterated checkpoint and test it under Halogen 0.20.4. r2 is peonist's stock v2 checkpoint with 149 tensors replaced by orcarouter's abliteration. Its author tested it on Halogen 0.15.0 only. This ticket also adds the trial manifest support and the Halogen checkpoint override described in the [spec](../spec.md#launcher-and-manifest-changes).

**Blocked by:** None.

**Status:** resolved

Source: [Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated](https://huggingface.co/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated) at revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`. The file of the same name on `main` is a different, never-run conversion; do not use it.

| File | Bytes | SHA-256 |
|---|---|---|
| `qwen38-flash-next-v2-abliterated.hgn` | 88,737,777,792 | `7bbac319851b500639462133085156b4f998dec562f511e65ca1c14d7af5163e` |

Put it in `/home/bogdan/models/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated/` with reflink copies of the stock `qwen38-flash-next-ngram.hgn`, `qwen38-flash-next-vision.hgn` and `tokenizer/` from the peonist directory. r2 was built against companion files whose hashes match the pinned ones.

- [x] `bin/models.sh` handles a trial manifest and `bin/run.sh halogen` takes an explicit checkpoint override; the stock default is unchanged, the README documents both, and the offline tests pass.
- [x] The file is downloaded and its size and SHA-256 verified (88.7 GB).
- [x] Halogen's `verify` and `inspect` run on r2, with their output lines recorded. r2 keeps 22 GB of replaced payloads unreferenced, so note anything `verify` says about them.
- [x] `ppl` compares r2 with the stock v2 checkpoint on the WikiText-2 raw test split ([checkpoint tools](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/checkpoint-tools.md); corpus kept outside the repository). The card reports perplexity 3.134 against 3.144, KL 0.060 and 92.2% top-token agreement on 0.15.0 over only 70,774 tokens; the full test split is 297,053 tokens, so absolute scores are not directly comparable.
- [x] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `halogen`, with the stock checkpoint as the control for the refusal probe.
- [x] Startup allocation and decode speed are recorded against stock v2 (the card claims the same 62.1 GiB of weights and the same speed).
- [x] Results are recorded in `docs/engine-updates.md`, and the r2 status in `docs/abliterated-models.md` is updated from "author-tested on 0.15.0 only".

## Comments

- November 15: ticket 01 also supplies shared CLI/dashboard weight profiles and alternative download manifests at the user's request. Register this trial in `config/weights.json` and follow `docs/weight-profiles.md`; model and Gufo MTP selection now come from the profile. Extension installation/loading still needs its own implementation and validation.

- Started November 15 after committing ticket 01 as `be16e13`. Registered `halogen/abliterated-r2` with a pinned six-column download manifest; stock companions are reflink copies. Upstream r2 bytes/hash rechecked before download. Stock control refused all five probes and passed all five exact identifiers. Preparing a full WikiText-2 reference with Halogen 0.20.4; corpus and reference are outside Git.

- Native verification finding: the pinned file passes SHA-256, but Halogen 0.20.4 `verify` reports 149 overlaps because the r2 replacements were appended and table entries are not in file-offset order. `check_hgn_layout.py` independently finds zero physical overlaps, duplicate names or out-of-bounds ranges. A temporary reflink copy with only table entry order changed passes the same native verifier (all 2,015 tensor checksums and payload checks; geometry checked on 1,197 tensors, 818 have no rule). That diagnostic copy was removed. The original, unchanged r2 is used for inference and the full-corpus comparison; keep this verifier limitation in the final record.

- Completed November 15: all nine manifest hashes passed; the original r2 passed full WikiText-2 scoring (297,052 positions), smoke/live conversation/tools/cancellation, all five exact identifiers and all five refusal probes. Allocation matched stock at 78.7 GiB; decode was modestly slower on the two measured requests. Full results and the native verifier limitation are in [the update record](../../../docs/engine-updates.md#november-15-halogen-r2-abliterated-trial). The final stop released memory; no engine or helper remains running.
