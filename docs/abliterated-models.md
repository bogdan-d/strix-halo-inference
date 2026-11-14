# Abliterated Flash-Next builds

Notes from November 15, 2026, for a later trial. Nothing here is provisioned, downloaded or run on this host. Numbers come from model cards and GGUF headers read with HTTP range requests; author measurements are their claims, not local results. Abliterated models answer requests the base model refuses and have no built-in guardrails.

## Picks

All three picks derive from one source, so the same uncensored model is available on every engine. None of the three repositories is gated.

| Engine | Repository | Download | Status |
|---|---|---|---|
| Halogen (first choice) | [Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated](https://huggingface.co/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated), revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`, file `qwen38-flash-next-v2-abliterated.hgn` (r2) | 88,737,777,792 bytes, SHA-256 `7bbac319851b500639462133085156b4f998dec562f511e65ca1c14d7af5163e` | Author-tested on Halogen 0.15.0 only |
| Gufo, and Halogen as a GGUF | [NeosQ/Qwen3.8-Flash-Next-Uncensored-UD-Q4_K_XL](https://huggingface.co/NeosQ/Qwen3.8-Flash-Next-Uncensored-UD-Q4_K_XL) | About 104 GiB in 3 shards, plus its own MTP head | Author-tested on Gufo `aae1ac48` (October 25) |
| Strixite | [ngkzngkz/Qwen3.8-Flash-Next-Uncensored-strixw](https://huggingface.co/ngkzngkz/Qwen3.8-Flash-Next-Uncensored-strixw) | About 114 GiB | Converted with Strixite v0.2.4; no published test |

For a single download, take the Halogen r2 file. Add NeosQ to have an abliterated model on the open-source engine.

### Halogen: Quat3rnion r2

r2 is peonist's stock v2 checkpoint with 149 tensors replaced by the orcarouter abliteration, re-encoded in v2's own 4-bit HT format with calibrated rounding; everything else is byte-identical to stock. Its card reports, on Halogen 0.15.0: WikiText-2 perplexity 3.134 against 3.144 for stock v2 (KL 0.060, same top token 92.2% of the time), about 53 tok/s greedy like stock, startup about 31 s and 62.1 GiB resident weights like stock. It answered all six test prompts stock v2 refused, called a required tool correctly and read a test image. The card also lists an abliterated IQ4_XS GGUF on the same engine at 43 tok/s, about 3 minutes to start and 68.3 GiB resident.

It needs only the main file. r2 was built against peonist revision `5cc17cea1a10b502b4a5db41d8d2b1a0f22dba26` for the n-gram table and `e053f488b120b99ed2525e6ac99f68c51b3b6179` for the tokenizer and vision files; their Hugging Face LFS hashes match the files at this repository's pinned revision `506567c641cfb737e0b01c1deff10813154c5529`, which are already on disk. Selecting it is a `HALOGEN_CHECKPOINT` change.

Pin r2 by revision. The repository's current file at the same name is a later native conversion (October 11, 66,687,678,432 bytes, SHA-256 `b5bd925fa2b44343be4a2cd328cae6b57ce7ffa2fe2cc56281717377e5a1ce8a`) made from the BF16 source with Quat3rnion's Apache-2.0 [bf16-to-hgn](https://github.com/Quat3rnion/bf16-to-hgn) converter. It has passed only offline format checks, never GPU inference, and its source-matched n-gram and vision files are not published; the author does not vouch for the stock companions with it. The repository also holds an experimental `qwen38-flash-next-ht43-abliterated.hgn`, likewise never run.

Before relying on r2 under 0.20.4, check it with the image's own [checkpoint tools](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/checkpoint-tools.md): `verify` and `inspect` for the file, `ppl` against the stock checkpoint, then the usual launch checks. Halogen's maintainers will not build refusal removal into the engine ([#239](https://github.com/peonist-ai/halogen-flash-server/issues/239)) and point to loading your own checkpoint.

### Gufo: NeosQ

NeosQ quantised the orcarouter BF16 weights with Unsloth's `UD-Q4_K_XL` type table and Unsloth's imatrix, re-split into 3 shards, and ships an MTP head built from the same weights (not Unsloth's stock head). Its header matches Unsloth's layout type for type: experts Q4_K, Q5_1, Q8_0 and Q5_K, the n-gram table IQ4_NL, embeddings and output Q8_0, and the four tensors behind Gufo's tool-identifier corruption ([gufo-org/gufo#780](https://github.com/gufo-org/gufo/issues/780)) kept at F32. The author reports MTP on, 31 to 38 tok/s and four jailbreak probes passed on Gufo `aae1ac48`, before the #780 fix; tool calling is not mentioned. Memory in Gufo should match the stock model, about 89 GiB at full context with MTP. Halogen also reads this layout as a GGUF, with its own draft head, about 4 GiB more RAM and slower decode than a native checkpoint.

### Strixite: ngkzngkz

ngkzngkz converted orcarouter's weights with Strixite's own [conversion recipe](https://github.com/shawnshekari/strixite/blob/main/docs/tools.md) (v0.2.4, vision tower added with v0.3.0). The files match the layout and sizes of the pinned `wemoh` package: 65.86 GiB of weights with Q4 routed experts, a 48.28 GiB Q8 n-gram table and a 0.84 GiB BF16 vision tower. Whether Strixite 0.7.0 reads files from that converter version is unverified. Strixite's `tools/convert_qwen4exp.cpp` can convert a BF16 source locally instead.

## Sources

| Source | Method | Notes |
|---|---|---|
| [orcarouter/Qwen3.8-Flash-Next-Uncensored](https://huggingface.co/orcarouter/Qwen3.8-Flash-Next-Uncensored), revision `8336e613ea508b13c2159bd0f68965d97a606b95` for Quat3rnion r2; NeosQ and ngkzngkz do not state theirs | Abliteration after Arditi et al. 2024: one refusal direction from the residual stream, projected out of the residual writers; MTP head abliterated consistently; no fine-tune | Gated BF16. The card says Apache-2.0, but the shipped LICENSE is the Qwen Community License 1.0, which derivatives follow. The most common source by far |
| [trohrbaugh/Qwen3.8-Flash-Next-heretic-2](https://huggingface.co/trohrbaugh/Qwen3.8-Flash-Next-heretic-2) | Heretic (custom fork) with per-layer directions on `o_proj` and `down_proj` | Author reports KL 0.0818 and 0 of 100 refusals against 99 for the base; Qwen Community License |
| [huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated) | huihui's abliteration; v2 leaves the experts unablated | Its `unsloth-UD-Q4_K_XL` GGUF folders state "GGUFs come from unsloth"; whether they hold the ablated weights is unclear |

A gated source needs `HF_TOKEN` (see the README) with access to public gated repositories, and the gate accepted on the model page.

## What each engine reads

**Gufo 0.34.0** loads Flash-Next experts only as Q4_K, Q5_K, Q6_K, Q5_1 or Q8_0 and the n-gram table only as IQ4_NL, Q8_0 or BF16 (see [smaller quants](gufo-extensions.md#smaller-flash-next-quants)). Header scans on November 15:

| Repository | Size | Loads | Notes |
|---|---|---|---|
| NeosQ/Qwen3.8-Flash-Next-Uncensored-UD-Q4_K_XL | 103.68 GiB | Yes | Pick, above |
| SenseiHans/Qwen3.8-Flash-Next-Uncensored-Q4_K_XL-Gufo | 103.48 GiB | Yes | Requantised from orcarouter's Q4_K_S, so double-quantised; stock MTP head |
| vmlinux/Qwen3.8-Flash-Next-Uncensored-Gufo-Q4Mix-GGUF | 102.23 GiB | Yes | The #780 file: four tensors at Q8_0, which Gufo 0.34.0 now expands to F32 at load with a warning |
| snappycrow/Qwen3.8-Flash-Next-Uncensored-GUFO-GGUF | 103.68 GiB | Yes | Three-line README, metadata names Unsloth; provenance unverifiable; stock MTP head |
| huihui-ai abliterated v1 and v2 GGUF, `unsloth-UD-Q4_K_XL` folders; htdohk/Huihui-Qwen3.8-Flash-Next-abliterated-MTP-GGUF | 103.68 GiB | Yes | Provenance unclear, above; htdohk adds Unsloth's stock MTP heads |
| HxT9/Qwen3.8-Flash-Next-Uncensored-Q4_K_M-Ngram-Q8_0 | 128.84 GiB | No | Q5_0 experts, Q4_K embeddings, too large |
| spiritfather/Qwen3.8-Flash-Next-heretic-2-GGUF | 130.76 to 141.30 GiB | No | Q5_0 experts in Q4_K_M; Q5_K_M passes types but does not fit; zeroed `compress_ratios` metadata |
| mradermacher/Qwen3.8-Flash-Next-Uncensored-GGUF and -i1-GGUF | 110.96 GiB (Q4_K_M) | No | Q5_0 experts and n-gram table, Q4_K embeddings |
| orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF | — | Not scanned | Gated; its Q4_K_M likely matches the mradermacher layout |

**Halogen 0.20.4** reads GGUFs whose tensors use the IQ4_NL, IQ4_XS, IQ3_S or Q4_0 family, Q8_0, Q6_K, Q4_K, Q5_K or Q5_1, and Q5_0 except on the gate/up experts ([GGUF guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/gguf.md)). It refuses Q4_1, Q2_K, Q3_K and the IQ2 and IQ1 families by name, and refuses a file re-encoded from an already quantised one, which likely excludes SenseiHans. It uses its own draft head with any GGUF trunk, and its `convert` mode writes a GGUF to a native `.hgn` once. Abliterated IQ4_XS GGUFs such as `wy2pay/Qwen3.8-Flash-Next-abliterated-GGUF-IQ4XS` should load in Halogen; none was scanned. [johnlockejrr/Swift-1.5-Qwen3.8-Flash-Next-heretic-HGN](https://huggingface.co/johnlockejrr/Swift-1.5-Qwen3.8-Flash-Next-heretic-HGN) is a native checkpoint of a different fine-tune (Swift 1.5, Swift Open License 1.0), not yet run in Halogen by its author.

**Strixite** reads only its own strixw format; besides ngkzngkz's build, Hugging Face lists strixw conversions of Swift 1.5 and ThinkingCap, both fine-tunes.

## Trial plan

1. Download the r2 file by revision into a new directory beside the stock checkpoint, verify its size and SHA-256, and run Halogen's `verify`, `inspect` and `ppl` against the stock checkpoint.
2. Start Halogen with `HALOGEN_CHECKPOINT` pointing at it, then run the health check, a real generation, `tests/live.py`, a refusal probe and the startup allocation, and record the results in the update record.
3. If an abliterated Gufo model is wanted, repeat with NeosQ in its own manifest, including tool calling, since #780 showed abliterated quants can change copied identifiers.

The launcher has no checkpoint override today, so a trial needs either a temporary manual `podman run` or a small explicit setting added to `bin/run.sh` and its manifest handling.
