# 01: Partial disk-cache restore changes greedy output on the Gufo IQ4_XS extension

Status: needs-triage

After a restart, a prompt that is partly restored from the disk prompt cache can produce different text at temperature zero than the same prompt prefilled from scratch. No adapter is involved. Found on November 21 while testing LoRA support for the `flash_next_iq` extension, and reproduced on the unmodified extension, so it predates that work.

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

## Suspected cause, not verified

Read from the extension's code by a reviewer, not confirmed by experiment: `WidePrefill` switches at more than eight rows (`src/kernels/rocm/executor.cpp:105` and `:3160`). A full prompt, or a nine-token remainder, takes the F16 GEMM route. A seven-token remainder takes the quantized GEMV route for the Q6_K attention output. Both are valid, but their logits differ slightly, which is enough to change a greedy continuation. This fits the table: the one prompt with nine tokens left is the one that stayed identical.

## Why it matters

- **Reproducibility:** a temperature-zero reply depends on what the disk cache holds, so two runs of the same request can differ across a restart.
- **Comparisons:** side-by-side tests of weights or builds must run without a disk cache, or each from an empty one. The LoRA equivalence checks did this after the first attempt showed the effect.
- **Quality:** not assessed. Nothing here shows either route is wrong.

## Open questions

- Does the built-in UD-Q4_K_XL provider in stock Gufo show the same fresh-versus-restored difference? Not tested.
- Is the difference only the kernel route, or does snapshot serialization contribute? A same-process run that splits the prefill at the same token boundary without disk I/O would separate the two.
- Does it occur at the launcher's native 262144 context with MTP on? The reproduction used 32768 and MTP off.

## Next steps

1. Repeat run A and run B on the built-in provider with the pinned upstream image.
2. Run the same-process split-prefill control and compare the first generated token IDs, or logits if a tool exposes them.
3. Decide between documenting it as expected behaviour and reporting it upstream: to [storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension) if only the extension is affected, or to [gufo-org/gufo](https://github.com/gufo-org/gufo) if the built-in provider reproduces it.

## Evidence

Logs are outside this repository, under `/var/mnt/xdata/code/strix-halo/gufo-build/iq/logs/`: `settle-a.json` and `settle-b.json` (replies of run A and run B), `gpu-settle-b.log.server` (restore events with 16, 20 and 20 tokens), and `gpu-s2-new-stock.log.server` (the first sighting).
