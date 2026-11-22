# 01: Partial disk-cache restore changes greedy output on the Gufo IQ4_XS extension

Status: resolved

After a restart, a prompt that is partly restored from the disk prompt cache can produce different text at temperature zero than the same prompt prefilled from scratch. No adapter is involved. Found on November 21 while testing LoRA support for the `flash_next_iq` extension, and reproduced on the unmodified extension, so it predates that work.

The [November 22 investigation](#2026-11-22--stock-gufo-and-the-live-prefix-control) reproduced the divergence on IQ4_XS without disk I/O and traced it to the extension's Q6_K prefill kernel selection. Stock Gufo's built-in UD-Q4_K_XL provider matched the fresh replies in both tested configurations.

## Observed

Setup: `flash_next_iq` 0.2.0 at `9ce08cef` on the pinned Gufo 0.35.0 runtime image, stock UD-IQ4_XS, `--context 32768`, one session, MTP off, thinking off, temperature zero, `--cache-disk` on a new empty directory. Run A sends three short prompts. Run B restarts the server on the same cache directory and sends the same three prompts.

| Prompt | Prompt tokens | Restored from disk in run B | Prefilled in run B | Run A reply | Run B reply |
|---|---:|---:|---:|---|---|
| Sky colour, three sentences | 23 | 16 | 7 | 414 characters | 418 characters, diverges at character 55 |
| Fibonacci function | 29 | 20 | 9 | 289 characters | identical |
| Lock-picking request | 27 | 20 | 7 | 510 characters, stops at 85 tokens | 945 characters, diverges at character 330, reaches the 200-token limit |

- Run A matches a run with no disk cache at all, on all three prompts.
- The refusal prompt refuses in both runs; only the continuation differs.
- The in-progress 0.3.0 build shows the same replies when it restores entries written by 0.2.0.

## Initial hypothesis

Read from the extension's code by a reviewer, not confirmed by experiment: `WidePrefill` switches at more than eight rows (`src/kernels/rocm/executor.cpp:105` and `:3160`). A full prompt, or a nine-token remainder, takes the F16 GEMM route. A seven-token remainder takes the quantized GEMV route for the Q6_K attention output. Both are valid, but their logits differ slightly, which is enough to change a greedy continuation. This fits the table: the one prompt with nine tokens left is the one that stayed identical.

## Why it matters

- **Reproducibility:** a temperature-zero reply depends on what the disk cache holds, so two runs of the same request can differ across a restart.
- **Comparisons:** for a full-prefill comparison of weights or builds, send `cache_prompt: false` on each request and verify that the response reports zero cached tokens. Disabling disk persistence alone still permits live prefix reuse.
- **Quality:** not assessed. Nothing here shows either route is wrong.

## Questions at filing

- Does the built-in UD-Q4_K_XL provider in stock Gufo show the same fresh-versus-restored difference? Not tested.
- Is the difference only the kernel route, or does snapshot serialization contribute? A same-process run that splits the prefill at the same token boundary without disk I/O would separate the two.
- Does it occur at the launcher's native 262144 context with MTP on? The reproduction used 32768 and MTP off.

## Original investigation plan

1. Repeat run A and run B on the built-in provider with the pinned upstream image.
2. Run the same-process split-prefill control and compare the first generated token IDs, or logits if a tool exposes them.
3. Decide between documenting it as expected behaviour and reporting it upstream: to [storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension) if only the extension is affected, or to [gufo-org/gufo](https://github.com/gufo-org/gufo) if the built-in provider reproduces it.

## Evidence

Logs are outside this repository, under `/var/mnt/xdata/code/strix-halo/gufo-build/iq/logs/`: `settle-a.json` and `settle-b.json` (replies of run A and run B), `gpu-settle-b.log.server` (restore events with 16, 20 and 20 tokens), and `gpu-s2-new-stock.log.server` (the first sighting).

## Comments

### 2026-11-22 — Stock Gufo and the live-prefix control

Stock Gufo 0.35.0 with the built-in Flash-Next UD-Q4_K_XL provider returned byte-identical text and the same stop reasons on all three prompts after a restart. This held at both 32,768 context with MTP off and 262,144 context with MTP on. Each pair used the pinned upstream image (`99e9b5471b7a`), the default weights, one session, and a separate empty cache for its first run. The fresh requests had zero cache hits. Both restarts restored exactly 16, 20 and 20 tokens from disk, leaving 7, 9 and 7 to prefill. At 256K the usage counters confirmed actual MTP drafting and acceptance. The prompts themselves were short in both configurations.

The original IQ4_XS extension (0.2.0, `9ce08cef`, no adapter) reproduced both divergences at 262,144 with MTP on. Its fresh and disk-restored replies each matched their 32K counterparts exactly, including the refusal changing from a stop at 85 tokens to the 200-token limit.

To isolate the prefill split, start a single 32K server with MTP off and no disk cache. Render a ticket prompt with `/apply-template`, tokenize it with `/tokenize`, and send just the first 16 or 20 tokens as text to `/v1/completions` with a one-token output limit. Immediately send the original chat request, then repeat it with `cache_prompt: false` for a full prefill. For each prompt the server reported `reuse=live` at the intended boundary and zero restored bytes. On stock, both the text and every returned top-two token-score record matched. On IQ4_XS 0.2.0, the live splits reproduced all three original disk-restored replies byte for byte, and the full prefills reproduced all three original fresh replies. The seven-token suffixes changed scores at the first generated token, with the first visible token differences at output tokens 11 (sky) and 56 (refusal), counting from one. The nine-token Fibonacci suffix matched throughout. Splitting prefill alone is sufficient to reproduce the symptom.

A diagnostic build of extension revision `9ce08cef` kept the wide Q6_K prefill route active for short suffixes. Changing only the attention-output projection made the sky reply match, but its scores still differed and the refusal still diverged. Extending that change to the generic Q6_K dense dispatch made all three live-split replies, stop reasons and every returned top-two token-score record match full prefill. The full-prefill controls also matched the unmodified extension. This isolates the width-dependent Q6_K dispatch as a group. The tests covered these three prompts and did not measure individual layer contributions or performance. [Extension dispatch](https://github.com/storm1er/flash-next-iq-gufo-extension/blob/9ce08cef17151aca3751ea2528765902054c54c4/src/kernels/rocm/executor.cpp#L1957) · [Attention-output projection](https://github.com/storm1er/flash-next-iq-gufo-extension/blob/9ce08cef17151aca3751ea2528765902054c54c4/src/kernels/rocm/executor.cpp#L3156)

The evidence points to the IQ extension for an upstream report. Stock Gufo's cache verification also expects greedy replay to match after a partial disk restore. [Gufo 0.35.0 cache verification](https://github.com/gufo-org/gufo/blob/0260e1162f8713caee4d3f4ff77e017de7165f9c/docs/internal/server.md#L335-L339)

Local evidence is under `/var/mnt/xdata/code/strix-halo/gufo-build/cache-restore-wnrA1dod/`. Run `python verify.py` there to check the response comparisons, reuse modes, restored byte counts, suffix lengths and MTP activity. The directory also contains the server logs, per-token score records, diagnostic patch (`probe.patch`) and build diagnostics (`checks.txt`). The diagnostic module was loaded from a separate store. All test containers were stopped and the temporary disk prompt caches were cleared.

### 2026-11-22 — Fix and launcher validation

The extension now selects Q6_K dense and attention-output prefill kernels independently of suffix length. Decode and speculative verification retain their existing kernel selection. The snapshot compatibility version is 21. On the first launch with the previous module’s 32K disk cache, all three ticket prompts had zero cache hits and produced their original fresh replies. On restart with newly written snapshots, the 7-, 9- and 7-token suffixes produced the same text, token counts and stop reasons.

The fork includes a real-weight regression test, `python3 tests/cache_replay.py`, that failed on `d7794c4` and passed on the fixed module. A further check compared live reuse with full prefill for every suffix length from one to nine tokens at 32K with MTP off. Text, finish reasons and all returned top-two token-score records matched at every length.

At 262,144 context with MTP on, both `iq4-xs` and `iq4-xs-lora` restored 16, 20 and 20 tokens from disk. On each profile all three replies matched its own fresh text, completion-token counts and stop reasons. Both profiles accepted speculative tokens and passed readiness, smoke generation, conversation recall, forced and streamed tools, disconnect and follow-up generation. All runs used short prompts. The fork tag `iq-cache-replay-1` points to the revision installed on this host and selected by the local launcher. [Fix commit](https://github.com/bogdan-d/flash-next-iq-gufo-extension/commit/5e262be42bc51202610899bfe32c22aad4b573b7)

Fix validation artifacts are under `/var/mnt/xdata/code/strix-halo/gufo-build/cache-fix-2JkQmSlg/`. `verified.txt` records disk reuse, suffix lengths and output lengths. `ar-restored.sweep` records the live-prefix checks. The build produced the same 207 compiler warnings as the preceding module. Listing the installed module with networking disabled produced one registry lookup warning and reported the module ready. All seven launcher starts printed the runc supplementary-groups notice and accessed the GPU. The servers logged no warnings or errors. Every test container was stopped and GPU memory returned to the desktop baseline.
