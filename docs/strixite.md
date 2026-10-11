# Strixite third-engine trial

Strixite is provisioned and has passed native-256K startup, readiness, short API tool and cancellation checks, guarded Pi read/edit/bash loops and shutdown on this host. The Pi checks used synthetic files inside a filesystem sandbox, not unrestricted access to real projects. Deep-prefill cancellation, restart-cache restoration and long-context workloads remain unvalidated. This is a controlled third-engine trial, not a replacement or a demonstrated performance upgrade. Read the [suitability assessment](strixite-research.md) and [performance evidence](strixite-performance-research.md) for the remaining risks.

Stage 1 added repository configuration, launch support and offline policy checks. Subsequent approval covered provisioning and the initial allocation and smoke gate, completed October 11, 2026. No host settings, existing Halogen or Gufo weights or live Pi configuration were changed. Strixite was stopped after the check, with no other containers running.

Further approval covered short API tool, streamed-argument and cancellation checks plus an isolated Pi tool loop, also completed October 11. The engine was stopped afterward. All runtime results below use the same pins and native-256K baseline.

The subsequent [sandboxed three-engine coding comparison](coding-comparison.md) passed its six-run smoke gate and all 36 matched trials. Strixite passed 12/12 trials across two tasks at off, medium and xhigh with the shared Bubblewrap boundary and strict JSON guard. It was close to Halogen at off but slower at medium and xhigh on mean task time. Its sampled MemAvailable floor was 19.13 GiB through the 12 short conversations. The engine stopped and memory release passed before cleanup. This supports continued evaluation, not replacement or unrestricted real-project use.

## Pinned inputs and defaults

`config/pins.env` pins release 0.2.3 to `ghcr.io/shawnshekari/strixite@sha256:9075d3def69d550b6c8f0b42a7795259ec02187ebf755027149f8c757d6cc738` and `wemoh/Qwen3.8-Flash-Next-strixw` to revision `e0be89740e7ac38f5ef0a911e0b91865431b7a01`. Registry and release metadata were rechecked October 11, 2026 without pulling or executing the image. The release source is `dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6`. Metadata correspondence is not signed provenance or runtime validation.

`config/strixite-files.tsv` selects the publisher's six checksum-manifest files: the main strixw v4 weights with included MTP tensors, the n-gram table, tokenizer, generation configuration, model configuration and license. Total additional storage is approximately 114.1 GiB before images, partial files and cache. Existing Halogen HGN and Gufo GGUF weights are not reusable. The package belongs under `/home/bogdan/models/wemoh/Qwen3.8-Flash-Next-strixw`.

| Setting | Launcher baseline |
|---|---|
| Container | `strix-halo-strixite`, rootless Podman |
| API | `http://127.0.0.1:5300/v1`, model `qwen3.8-flash-next` |
| Readiness | `/health`, JSON `status: ok`; inspect degradation separately |
| Context | `--capacity 262144 --rope-yarn-factor 1`, native 256K without YaRN extension |
| Speculation | `--mtp on`, disable with `SPECULATIVE=off` |
| Model store | Entire central store mounted read-only at `/models` |
| Model selection | `STRIX_MODELS_DIR=/models/wemoh/Qwen3.8-Flash-Next-strixw` |
| Writable cache | `$HOME/.cache/strix-halo-inference/strixite` at `/cache`, explicit `--prompt-cache-dir /cache` |
| Cache limits | `--prompt-cache-gib 16 --prompt-cache-ram-margin-gib 8` |
| Low memory | `--low-memory fail`, no automatic adaptation or restart |
| Thinking nudge | `--think-nudge off` |
| Stop timeout | 90 seconds, both container default and managed stop |

The upstream image entrypoint reads its bundled configuration. Launcher flags override it. Other release defaults remain in effect: 16384-token prefill chunks, thinking on unless a request disables it, five MTP drafts, end-of-turn guard on, literal-tag handling on, approximately 3 GiB CPU n-gram row cache, 32 GiB cache filesystem-free margin and 32 GiB/hour cache write budget. A 16 GiB disk-cache cap is not a RAM cap. The 8 GiB RAM margin is not a desktop memory reservation. The startup memory check runs after GPU allocation.

`MODELS_DIR` and `CACHE_ROOT` use the same host overrides as the existing engines. `CONTEXT` can reduce Strixite capacity within 4096..262144; YaRN stays at factor 1. Changing context or speculation requires stopping and restarting, and client context must be set independently. Changes to weights, MTP or YaRN can invalidate saved states.

## Provision and launch

Recheck upstream compatibility and host free disk space before provisioning on another host or selecting new inputs. The pinned package is already downloaded and fully hash-verified on this host. These commands pull or execute an upstream image and download or verify weights:

```bash
bin/run.sh strixite pull
bin/run.sh strixite diagnose
bin/models.sh download strixite
bin/models.sh verify strixite
```

`diagnose` runs the release's `--help` with networking disabled and exits before model allocation. It confirms the CLI can execute, not that GPU allocation or inference works. The release has no dedicated GPU diagnostic command. Downloading resumes partial files and verifies hashes before promotion. The final `verify` reads all selected files and must finish successfully before the first launch. Existing corrupt files are rejected rather than replaced. Startup only performs the fast presence and size check.

Stop any active engine and verify host memory release before starting Strixite. The existing shared startup lock and managed-engine label block another managed engine from starting while one is running. They do not detect unrelated inference processes, desktop GPU consumers or containers launched outside this helper. Do not run a sidecar model during this trial.

```bash
podman ps
free -h
bin/run.sh strixite start --wait
bin/run.sh strixite status
bin/run.sh strixite logs --follow
bin/run.sh strixite smoke
bin/run.sh strixite stop
```

`start --wait` has the same bounded readiness wait as the other engines, defaulting to 300 seconds via `START_TIMEOUT`. Timeout or interruption leaves the container available for inspection. Read logs before stopping because the container is auto-removed on exit. `smoke` requests at most 32 output tokens with thinking explicitly disabled through `reasoning_effort: none`. It checks readiness and nonempty generation, not coding quality or tool safety.

`status` reads the running container's actual image, arguments and cache mount. It reports context, MTP, YaRN, nudge, low-memory policy, disk cap and RAM margin. Health reports active context and any degradation. An HTTP-successful `status: ok` is readiness even when degradation is reported, so review that field before accepting the baseline. Engine GPU allocation and cache RAM usage remain unavailable rather than inferred. Host RAM and kernel GTT are separate accounting views and must not be added together.

The launcher passes the existing GPU devices and requests unlimited memlock, which rootless Podman may clamp. On this host, runc receives no `keep-groups`. No privileged mode, host IPC, unconfined seccomp, label disablement or writable host control mount is added for Strixite. If ordinary device access fails, investigate and obtain approval before changing permissions, security or host boot settings. Keep the current GTT limit and `iommu=pt`.

## Local allocation and smoke results

Measured October 11, 2026 using the pinned release and model revision above. The six selected files passed download-time SHA-256 checks and a separate full final-file verification. The image's `--help` and inference ran under rootless runc with ordinary GPU device access. No security, device permission, kernel, BIOS or IOMMU changes were needed. The endpoint was published only at `127.0.0.1:5300`.

| Observation | Local result |
|---|---|
| Capacity and serving flags | 262144 tokens, YaRN factor 1, MTP on, thinking nudge off, low-memory fail |
| Launcher to readiness | 14.75 seconds, including container creation and readiness polling |
| Weight load | 65.9 GiB in 12.5 seconds, reported by startup log |
| GPU buffers | 84.6 GiB in 69 buffer kinds, reported by startup log |
| CPU n-gram row cache | 3.0 GiB, reported by startup log |
| Startup memory check | 29.3 GiB MemAvailable after loading, above the reported 14.8 GiB requirement |
| Health | `status: ok`, expected model, `context_length: 262144`, no degradation field |
| Bounded generation | Reply `ready`, 17 prompt tokens, 2 completion tokens, zero reasoning tokens, `finish_reason: stop` |
| Request timing | 0.21 seconds server total, approximately 0.16 seconds to first token; launcher smoke command 0.264 seconds |
| Short cache export | 116 MB state exported to RAM in 22 ms, reported by request log |
| Managed stop | 0.754 seconds, within the 90-second allowance; container auto-removed |
| Host MemAvailable | 117.90 GiB before, sampled minimum 28.37 GiB, 117.75 GiB two seconds after stop |
| Kernel GTT usage | 0.852 GiB before, sampled maximum 85.82 GiB, 0.854 GiB two seconds after stop; limit unchanged at 105.46875 GiB |
| Host swap usage | 7.18 MiB before, sampled maximum and after 7.43 MiB |

Host memory and GTT were sampled roughly once per second through startup, smoke and stop, with 20 observations. Shorter peaks may have been missed. Memory-pressure cumulative counters increased by approximately 0.207 seconds for both some and full stall time over the trial; these host-wide readings do not isolate Strixite from desktop activity. GPU-buffer accounting in the engine log and kernel GTT usage are different views, not interchangeable or additive quantities. The observed 84.6 GiB buffer report is below the earlier publisher-derived 88.6 GiB estimate, but does not establish deep-context peak memory.

The model files had just been read for full integrity verification, so startup timing is not a cold-storage benchmark. A two-token response does not establish throughput or MTP quality; its one draft was rejected. Thinking was disabled explicitly for the request, while the server's default remains on. The post-response health probe still reported busy, followed by a completed request log with the RAM cache export; slot-release latency was not measured. The one-shot cache entry was logged as RAM-only and the cache directory remained empty after stop. Disk flush, restart restoration and full-capacity saved states were not exercised.

## API tools, cancellation and guarded Pi results

`tests/strixite_live.py` is a Strixite-only live check. It passed multi-turn recall, automatic tool selection, a tool-result follow-up and streamed arguments containing literal `<|im_end|>`, `<tool_call>`, `</tool_call>` and `</think>` text. The streamed call's 22 argument fragments assembled into strict JSON and preserved the expected string. Returned tool calls are inspected, never executed by this API check. The existing `tests/live.py` forced-tool checks for Halogen and Gufo were not changed.

A deliberately 12-token-limited tool response ended with `finish_reason: length`, one invalid partial argument JSON string and the engine's `dropped_partial_tool_call: true` and `malformed_tool_calls: 1` flags. These partial arguments were not repaired or executed. Short-prompt streamed decode was disconnected after content arrived, with health confirming the request was still busy before disconnection. Health reported the execution slot idle after 0.253 seconds, and a subsequent generation returned `ready`. This measures short-prompt decode cancellation only, not cancellation during a deep 16384-token prefill chunk. The Strixite check has a separately documented 60-second failure bound and reports measured latency; the existing engines' 20-second assertion remains intact.

Installed Pi 1.1.0's OpenAI adapter uses best-effort JSON repair and incomplete-object parsing even when finalizing tool arguments. Its standard agent loop explicitly refuses execution for all tool calls in a `stopReason: length` response, but schema validation alone does not detect a repaired, truncated string under other finish reasons. Do not infer that a finalized Pi tool-call object proves the original streamed JSON was complete.

The isolated check therefore loads the test-only [strict argument guard](../tests/strixite_guard.ts). It buffers original argument deltas, requires strict `JSON.parse` to produce an object from a successful tool-call response and blocks any call without that evidence before execution. [Offline guard checks](../tests/strixite_guard.mjs) exercise complete fragmented arguments, truncated arguments beside a complete sibling, length/error/abort/stop refusal and approval isolation between turns. The guard is not installed in live Pi and is not a general command-approval or shell sandbox policy.

`tests/strixite_pi.py` creates temporary agent settings and synthetic Python files, copies the guard there and runs the entire Pi process through existing Bubblewrap. Only `/usr` and the existing `/home/linuxbrew/.linuxbrew` installation are exposed read-only, plus the temporary writable test directory. The boundary check confirms `/home/bogdan`, the model store, repository paths and GPU devices are absent. The process environment is cleared, discovery of host extensions, skills and context is disabled, and sessions are not retained. Host networking remains shared for the localhost API, so this is filesystem and process isolation, not a network sandbox. Temporary test files and captured JSON events are deleted after the run. Hashes of live Pi `models.json` and `settings.json` remained unchanged.

The current runner uses the shared [coding-test boundary](../tests/pi_sandbox.py), also enforced by the Halogen/Gufo thinking comparison. It mounts only the current synthetic workspace writable, with immutable configuration and guard files inside an ephemeral agent directory. Pi's runtime locks and empty authentication file stay in that ephemeral directory. No sibling workspaces or inference caches are exposed. Independent acceptance code uses the same sandbox. The original results below used the earlier Strixite-only boundary; that exact literal-tag model loop has not been repeated after consolidation. Real model-driven use of the shared boundary subsequently passed on the two different tasks in the [matched coding comparison](coding-comparison.md).

| Isolated Pi mode | Local result |
|---|---|
| Pi and Node | Pi 1.1.0, Node 26.11.1, existing installations |
| Thinking off | 7.574 seconds, five successful tool calls covering read, edit and bash, no reasoning output |
| Thinking medium | 14.087 seconds, five successful tool calls covering read, edit and bash, 1623 streamed thinking characters |
| Independent verification | Positive, negative and singleton list cases passed; test code and literal-tag fixture remained unchanged |
| Recall through tools | Both runs reported the marker read from the literal-tag fixture |
| Strict argument guard | All executed calls approved from complete original JSON; no blocked call or tool error in either run |

The temporary Pi profile derives from the public Halogen profile, points only to localhost:5300 and advertises 262144 context with a 16384 completion cap. The thinking-level mapping is unchanged. The off override changes presence penalty from 1.5 to 0 because Strixite rejects nonzero penalties. Thinking-enabled sampling remains temperature 1, top-p 0.95 and top-k 20. Retry is disabled for this bounded check. These are two synthetic runs, not a statistically controlled thinking comparison, an xhigh validation or proof of real-project coding quality.

To repeat on this host, first start only Strixite and wait for readiness. The Pi check requires the existing Bubblewrap and Homebrew layout. The offline guard check requires a Node release with built-in TypeScript stripping. No installation is performed by these checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/pi_sandbox.py
node tests/strixite_guard.mjs
bin/run.sh strixite start --wait
python tests/strixite_live.py
python tests/strixite_pi.py
bin/run.sh strixite stop
```

The live checks require an already-running engine and do not own its lifecycle. If a check fails or is interrupted, inspect logs and explicitly stop the engine. No live Pi provider, guard or default was installed by these tests. Unrestricted Pi use remains deferred until a separately reviewed client safety and isolation policy is selected.

After the API and Pi checks, managed stop succeeded and host MemAvailable returned to approximately 120 GiB, with kernel GTT usage approximately 0.60 GiB and no running containers. The cache directory held approximately 1.34 GiB on disk after clean stop. This exercises short-session shutdown persistence, not successful restoration or deep-state disk flushing.

## Remaining runtime acceptance gates

Successful 256K allocation is only the first gate. Extend memory measurements through realistic generation, deep cache export and shutdown. The initial local startup log confirms a 14.8 GiB post-load requirement at this configuration, but neither that check nor the short trial guarantees safe near-capacity operation. Stop on GPU errors or unsafe memory pressure rather than tuning the host automatically.

- Repeat health, expected model, native context and bounded generation after any image or model change. Inspect degraded settings and confirm startup flags in logs. This gate passed for the current pins.
- Extend automatic-tool, streamed-argument, recall and guarded Pi checks to realistic coding workloads. Short synthetic checks passed, including literal model tags and deliberate truncation. Do not permit repaired partial JSON to execute commands, and do not silently drop the guard or isolation for real projects.
- Measure disconnect cancellation and generation afterward at increasing prompt depth. The inherited 16384-token chunk can delay cancellation to a chunk boundary, reportedly around 25 seconds at depth. Record latency rather than silently relaxing the existing engines' 20-second check.
- Compare MTP and plain greedy output on uncached prompts, then validate clean stop, restart-cache restoration and compatibility after configuration changes.
- Increase realistic coding and retrieval prompts toward native 256K, leaving space for output. Measure quality and peak memory, not just decode speed. Compare matched sampling, thinking, power and cache conditions against the existing engines. Different quantization makes this a practical setup comparison, not a pure engine benchmark.

## Pi and deferred integration

The shared [Pi profiles](pi.md) now include Strixite at localhost:5300, model `qwen3.8-flash-next`, native 262144 context and a 16384 output cap. Supported choices are off, low, medium and xhigh, with xhigh as the per-model startup default. Its compaction settings reserve 16384 tokens and retain 32768 recent tokens. The profile is installed in this host's live Pi configuration with private backups, preserving unrelated providers and global defaults. Readiness output prints its Pi selection command. The isolated coding checks now reuse this public profile instead of reconstructing it from Halogen. Normal Pi tools remain unsandboxed, and the strict argument guard remains test-only; provider installation does not validate unrestricted real-project use or install a tool-safety policy.

Strixite accepts ordinary `tool_choice: auto` but rejects named-tool selection and `required`. `tests/live.py` deliberately remains limited to Halogen and Gufo with its forced-tool requirement intact. Nonzero presence and frequency penalties are rejected, as is repetition penalty other than 1. In particular, do not copy the existing thinking-off presence penalty 1.5. Thinking-enabled temperature 1, top-p 0.95 and top-k 20 passed the isolated medium-thinking Pi loop and subsequent matched medium and xhigh coding trials. Deeper sessions remain untested.

`bin/update.sh` still updates only Halogen and Gufo and `--fresh-cache` archives only their cache directories. It preserves the Strixite pins and cache. Its active-engine guard also refuses rotation while managed Strixite is running. Until retention is justified, review and change Strixite image and version pins together manually, never changing its model revision implicitly. There is no Strixite Grafana dashboard, persistent service, chat UI, authentication or vision integration.

Offline checks cover launcher isolation, explicit arguments, stop timing, bounded smoke payload, running-container status, corrupt-file refusal and strict tool-argument gating. Local runtime checks establish initial allocation, health, short API tools and decode cancellation, guarded synthetic Pi loops and stop. They do not establish unrestricted Pi safety, deep-prefill cancellation, long-context quality, MTP consistency, restart-cache integrity or superiority over the existing engines. No persistent service is enabled.
