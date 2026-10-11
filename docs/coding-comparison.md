# Sandboxed three-engine coding comparison

All 36 matched coding trials passed on October 11, 2026 after the six-run sandboxed smoke gate passed. Halogen 0.17.5, Gufo 0.11.0 and Strixite 0.2.3 each completed the same two tasks at off, medium and xhigh, with two repeats per condition. Every run passed the original independent acceptance checks, preserved the check file, completed normally and passed the strict streamed-JSON guard. No live Pi configuration or normal engine cache was changed. Each engine stopped and released memory before the next started.

Halogen had the lowest mean task time at every effort level. Strixite was close to Halogen with thinking off, between Halogen and Gufo at medium, and close to Gufo at xhigh. These short tasks support retaining Strixite as a working third-engine candidate, not replacing Halogen or claiming general superiority. Two repeats per task do not establish a reliable speed ranking or equal coding quality. Native-256K allocation was configured, but these prompts were short.

## Matched results

Pi 1.1.0 used the unchanged image/model pins, balanced power profile and powersave CPU governor. The public [summary JSONL](coding-comparison-results.jsonl) records all trials, configuration fingerprints and memory observations without raw conversations or generated source. Mean task time includes Pi startup, inference and tools, but excludes engine loading and the independent final check. Output tokens include reasoning. Intermediate tool errors remained visible and all were recovered before final acceptance. No run timed out or ended with a length, error or aborted assistant stop reason. Every off run emitted zero thinking characters, and every medium and xhigh run emitted thinking.

| Engine | Effort | Passed | Mean task time | Tool calls | Output tokens | Intermediate tool errors |
|---|---|---|---|---|---|---|
| Halogen | off | 4/4 | 12.17 s | 24 | 2,837 | 1 |
| Halogen | medium | 4/4 | 23.41 s | 23 | 5,278 | 1 |
| Halogen | xhigh | 4/4 | 56.98 s | 35 | 12,884 | 0 |
| Gufo | off | 4/4 | 20.93 s | 28 | 3,413 | 2 |
| Gufo | medium | 4/4 | 32.09 s | 22 | 5,402 | 0 |
| Gufo | xhigh | 4/4 | 88.60 s | 34 | 14,407 | 2 |
| Strixite | off | 4/4 | 12.46 s | 23 | 2,790 | 0 |
| Strixite | medium | 4/4 | 28.16 s | 22 | 5,951 | 0 |
| Strixite | xhigh | 4/4 | 86.14 s | 39 | 18,554 | 1 |

The seven intermediate errors comprised six bash tool results and one Halogen edit result. Their source text was not retained, so these counts do not distinguish an intentional failing baseline test from an implementation mistake. Correctness here means satisfying the fixed cases, not a review of maintainability or every possible input. Off was fastest in each paired case and passed every check; that does not justify disabling thinking for complex work. Medium remained faster than xhigh in every paired case, consistent with the earlier [two-engine exploratory comparison](thinking-comparison.md).

### Memory and shutdown

Approximately one-second samples cover startup, all 12 trials per engine and shutdown. All three memory-release gates passed before switching. The final observation had no running containers, approximately 120.9 GiB MemAvailable and 0.675 GiB kernel GTT use. Swap use remained approximately 590.6 MiB rather than returning to its initial 26.5 MiB. Swapped pages can remain after the allocating process exits, and these host-wide readings do not identify which process owned them. No host tuning or forced swap clearing was performed.

| Engine phase | Samples | Minimum MemAvailable | Peak kernel GTT use | Peak swap use |
|---|---|---|---|---|
| Halogen | 399 | 93.00 GiB | 20.66 GiB | 26.53 MiB |
| Gufo | 633 | 28.78 GiB | 89.57 GiB | 762.80 MiB |
| Strixite | 528 | 19.13 GiB | 85.68 GiB | 591.79 MiB |

These are separate host accounting views, not engine footprint rankings. In particular, Halogen's pinned host-weight allocation is not fully represented by kernel GTT or MemAvailable. Strixite's lower observed available-memory floor developed during multiple short conversations with retained caches, so short-prompt success does not establish near-capacity headroom. Disk restoration after restart, deep cache states and deep-prefill cancellation were not exercised. Validate those and progressively longer context before unrestricted project use or persistent services.

## Repeat

Stop managed inference engines first. Use the existing pinned images and verified weights, Pi, Node, Bubblewrap and Homebrew installation. No downloads or installation are performed.

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/pi_sandbox.py
PYTHONDONTWRITEBYTECODE=1 python tests/thinking.py --self-check
node tests/strixite_guard.mjs
mkdir -p results
PYTHONDONTWRITEBYTECODE=1 python tests/coding.py --smoke > results/coding-smoke.jsonl
PYTHONDONTWRITEBYTECODE=1 python tests/coding.py --repeats 2 > results/coding-comparison.jsonl
```

Run the matrix only after the smoke command succeeds. Smoke runs one task at off and medium for each engine. The full matrix runs both public tasks at off, medium and xhigh, with two repeats per condition, for 36 trials. The second repeat reverses effort order. Halogen runs before Gufo, then Strixite, never concurrently. Individual Pi invocations have a ten-minute limit. A failed matrix task is recorded without discarding later observations; inspect each record's `passed` field rather than treating process completion as universal correctness.

The runner reuses the [fixed coding tasks](../tests/thinking_tasks.py) and [Pi event accounting and independent checks](../tests/thinking.py). Both Pi and acceptance code run inside the [shared sandbox](../tests/pi_sandbox.py). Only the current synthetic workspace is a writable host mount. Settings and the [strict argument guard](../tests/strixite_guard.ts) are read-only, with ephemeral runtime state and no live credentials, repositories, models, engine caches or GPU devices exposed to tools. Networking is shared for localhost inference, not isolated. The guard is enabled equally on all engines. No live provider or extension is installed.

All engines allocate native 262144 context with MTP on. Strixite additionally sets YaRN factor 1 and thinking nudge off through its existing launcher. Sampling is identical across engines at each effort: off uses temperature 0.7, top-p 0.8 and presence penalty 0; medium and xhigh use temperature 1, top-p 0.95 and neutral penalties. Top-k is 20, min-p is 0 and repetition penalty is 1. Preserved thinking remains enabled, and the completion cap is 16384. Zero presence penalty intentionally differs from the normal Halogen/Gufo off profile's 1.5 because Strixite rejects nonzero penalties. Retries are disabled. No fixed seed is imposed.

Workspaces and separate per-engine disk caches are created on disk under ignored `results/coding-*`, not in tmpfs or normal engine caches. Each engine starts with an empty disk-cache directory, retains prompt state across its trials and stops before temporary files are removed. OS file caches are not flushed. Model-visible paths stay `/workspace`, allowing prefix reuse. This is not a cold-cache benchmark. Live Pi models and settings are checked for byte-for-byte preservation. If an engine cannot be stopped, mounted temporary state is retained with its path reported.

Host MemAvailable, swap use and kernel GTT use are sampled approximately once per second through engine startup, trials and stop. Shorter peaks may be missed. Before switching engines, GTT must return within 1 GiB of that engine's pre-start baseline and MemAvailable within 8 GiB, allowing 30 seconds for release. These tolerances allow desktop activity and reclaimable page-cache changes, not concurrent model use. Host-wide metrics cannot isolate desktop consumers. Halogen's pinned host weights make MemAvailable and kernel GTT especially unsuitable as estimates of its complete allocation. Do not add these accounting views together or rank engine memory footprint from GTT alone.

## Smoke timings

Times include Pi startup, inference and tools, but exclude engine loading and independent final verification. These are single observations, not a speed ranking.

| Engine | Off | Medium | Final checks | Intermediate tool errors |
|---|---|---|---|---|
| Halogen | 22.64 s | 23.86 s | 2/2 passed | 3 off, 0 medium |
| Gufo | 19.27 s | 33.03 s | 2/2 passed | 1 off, 0 medium |
| Strixite | 12.08 s | 22.54 s | 2/2 passed | 0 |

An initial Halogen off observation passed final verification but stopped the first attempt because the initial smoke gate rejected every intermediate tool error. The gate was corrected to distinguish recoverable tool errors from final failure, and all six runs above used new temporary caches. No acceptance check was weakened. Raw conversations and generated code were not retained or published.

Different quantizations make this a comparison of complete setups, not pure inference-engine speed. Short synthetic tasks do not validate real-project judgment, long-context quality, deep-prefill cancellation or near-capacity memory safety.
