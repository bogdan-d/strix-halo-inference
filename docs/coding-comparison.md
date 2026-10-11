# Sandboxed three-engine coding comparison

The October 11, 2026 smoke gate passed six real Pi coding runs through the shared Bubblewrap boundary: the environment-parser task with thinking off and medium on Halogen 0.17.5, Gufo 0.11.0 and Strixite 0.2.3. Every run passed the original independent acceptance checks, preserved the check file, completed normally and passed the strict streamed-JSON guard. Halogen off had three intermediate tool errors and Gufo off had one; both recovered. These errors remain recorded rather than being treated as failed final tasks. No live Pi configuration or normal engine cache was changed. Each engine stopped and released memory before the next started.

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
