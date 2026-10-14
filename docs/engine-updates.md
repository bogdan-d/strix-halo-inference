# Engine updates

## October 14 update

`bin/update.sh` pulled the new Halogen and Gufo images by digest and atomically updated their image and version pins. Strixite `latest` still resolves to the pinned 0.2.4 digest. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged. The updater printed only the selected releases' notes during this run, so the Halogen 0.18.2 and Gufo 0.14.0 notes below were read from the publishers separately. The updater now prints the notes of every stable release after the pin, and a `--check` from the October 12 pins reproduced all four sections.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.1 | 0.18.3 | `sha256:b5c28a27c11af02fc907c9c263522f2fc9ad1bd27b470adceca081175952de32` |
| Gufo | 0.13.0 | 0.15.0 | `sha256:451341e2249d72c04f8ef159aebacbe3d14e0591888c19c77a26f3d183961936` |
| Strixite | 0.2.4 | 0.2.4 | `sha256:23411d0de807055c97ce885b0ac60cfe17609836bb0d5a5c39d3cbb891a34876` |

The release notes below are publisher claims. The [local checks](#october-14-local-checks) that follow them ran after the update, from a session not served by Halogen. The images advertise image revisions Halogen `293c940b140e` and Gufo `89d6185532ff6d5de0336000fc6ad62e869b82b6`; neither was compared with public source.

### Halogen 0.18.2 and 0.18.3

- **End-of-text handling (#173).** The model declares two end-of-text tokens and 0.18.1 stopped on one, so an affected reply ran on to `max_tokens` and returned empty or with text after the end. 0.18.3 stops on either. Nothing of that shape was seen in local sessions.
- **Queue visibility and abandoned requests.** A client that disconnects while its request is queued now leaves the queue instead of taking a slot when its turn arrives, and a request waiting more than 30 seconds logs what it waits for, again every five minutes. `/health` adds `longest_wait_s` beside `queued`, and `/metrics` adds `halogen:queue_waited_total`, `halogen:queue_wait_seconds_total`, `halogen:queue_wait_longest_seconds` and `halogen:queue_gave_up_total`, none of which the current relabel allowlist collects. The dashboard treats `/health` as a boolean only, so the added field changes nothing there.
- **Startup memory reading.** The budget now counts kernel `CmaFree` as unavailable on hosts that reserve it, so a post-restart `host memory left` figure may not be comparable with the October 12 check for that reason alone.
- **New startup line.** `HALOGEN_TEMPLATE_CHECK` defaults to `warn` and reports whether the loaded chat template re-renders a conversation the way the prompt cache needs to reuse earlier turns. The launcher sets nothing, so this line should be read after the first restart on 0.18.3.
- **Strict tool schemas (0.18.2, #147).** A tool declared `strict: true` gets a call that names one of the request's tools with arguments matching its schema, at any temperature; `HALOGEN_STRICT_TOOLS=0` accepts the field without enforcing it. Neither `bin/run.sh` nor the Pi profile sets that variable, and whether the Pi profile sends `strict` on its tools was not checked.
- **Structured output and template parsing (0.18.2).** A `response_format` schema with an open object or an array without `items` no longer stalls the server for about a minute the first time it is sent, a sampled request with a schema and tools starts its JSON as promptly as a greedy one, and chat-template markers typed inside a message, tool result or tool description now reach the model as characters rather than as the template's own markers (`HALOGEN_CLIENT_MARKERS=special` restores the previous behavior).
- **Old GPU firmware (0.18.2).** A host with GPU firmware predating 2026 no longer fails on prompts of about 70 to 2,000 tokens or on images: the server reads the firmware version and logs one line saying it runs as with `HALOGEN_QSA_FORCE_SEL=1`. This host's firmware state was not checked, so that line is worth looking for after the restart.
- **Checkpoints and cache format.** Both Halogen sections state the Flash checkpoints are unchanged and that temperature 0 output stays byte-identical to serial greedy decode. Neither mentions a prompt cache or snapshot format change, and whether the existing `/cache` contents are reused on 0.18.3 was not checked.
- **Not reachable from this launcher.** The NPU features added in 0.18.2 and 0.18.3, namely EmbeddingGemma 2 and WeMM-Embedding-4B on `/v1/embeddings`, `/v1/images/edits` and `/v1/images/variations`, the opt-in streaming guard and the longer decider texts, need NPU model names that `bin/run.sh` does not set. `max_tokens: -1`, the llama.cpp-shaped `/props`, `/slots`, `/tokenize` and `/detokenize` routes, Codex tool namespaces, opt-in `HALOGEN_FORK_MAP=auto` and the second-AMD-GPU selection including `HALOGEN_GPU_DEVICE` are likewise unused here, and the slower default NPU image generation is irrelevant without NPU image models.

### Gufo 0.14.0 and 0.15.0

- **0.14.0** wired Flash-Next serving to the component cache (#573) and added a ROCm managed-alloc fallback (#460).
- **0.15.0** pins Flash-Next cache pages without compacting host memory (#589), accepts response schemas without `additionalProperties`, accepts IPv6 listen addresses, which does not change the localhost-only endpoint used here, and speeds up wide prefill kernels for Qwen Flash (#571), a publisher performance claim that was not benchmarked locally.
- Neither release note mentions a cache or snapshot format change, so whether an existing prompt cache is reused or starts cold on 0.15.0 is unknown, as it already was for 0.13.0.

### October 14 local checks

All three engines were started one at a time at native 262144 context with `/dev/accel/accel0` newly passed in. Each passed the readiness check, `bin/run.sh ENGINE smoke` and its live API test, then released its memory on stop (GTT back to 1.5 GiB). The live tests cover a multi-turn conversation, a forced named tool, a streamed automatic tool, slot release after a short-decode disconnect and generation after that cancellation. No engine used the NPU.

- **Halogen 0.18.3.** Allocation 81.4 GiB: 62.1 GiB weights, 7.2 GiB KV pool, 12.1 GiB working memory, with 30.6 GiB host memory left. The new template check passed: "the history is reusable in 6 of 6 turn shapes and the model's own reply in 4". No old-firmware workaround line appeared. The startup also warned that 12.1 GiB of host RAM was in use before it started, which it says comes out of the file cache that serves the 47.7 GiB lookup table; prefill speed was not measured. Every previously allowlisted metric name is still exported, and the two queue metrics now collected were checked through a real scrape (see [Halogen dashboard](halogen-monitoring.md)). A request queued behind a running one, whose client hung up after six seconds, left the queue as 0.18.3 claims.
- **Halogen prompt cache.** 0.18.3 opened a new, empty cache directory under `/cache`. Earlier releases' directories, about 24 GB in four directories, are not reused and were left in place.
- **Gufo 0.15.0.** First start on this host, loading in 62 seconds. Metrics and readiness scrapes were up. 0.15.0's component cache ignores `--cache-disk-staging-bytes` and logs `option_ignored` with a 1 MiB staging capacity. The launcher still passes the flag.
- **Strixite 0.2.4.** Unchanged image, rechecked only because the launcher now passes the NPU device.

Not exercised: Pi sessions on the new versions, strict tool schemas, structured output, long-context quality, deep-prefill cancellation, prompt-cache reuse across a restart, dashboard rendering in a browser and any NPU workload.

Sources: [Halogen 0.18.2 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.2/CHANGELOG.md), [Halogen 0.18.3 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.3/CHANGELOG.md), [Gufo 0.14.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.14.0) and [Gufo 0.15.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.15.0).

### Reply-end reuse

After these checks, Halogen was switched to `HALOGEN_FORK=1` with `HALOGEN_FORK_MAP=auto`, new in 0.18.3. Without it, each turn reused the previous prompt from cache but processed the model's own previous reply again, reasoning included. In a recorded Pi session that was up to about 7,500 tokens per turn.

[`.scratch/fork-map/bench.py`](../.scratch/fork-map/bench.py) replays a Pi-shaped conversation at temperature 0, with tool calls, reasoning sent back and two follow-up questions, from an empty cache for each configuration. At `xhigh` effort, a follow-up question after a 1,396-token reply processed 1,430 tokens again and took 1.13 seconds to its first token without the setting. With it, a follow-up after a 1,970-token reply processed 35 tokens and took 0.23 seconds. Uncached tokens after the first request fell from 9,534 to 6,324; the remainder is new tool output. Greedy replies were not identical between the two configurations, so the turns differ in length. The two configurations were compared turn by turn rather than with a single throughput figure.

Startup allocation is unchanged at 81.4 GiB. Health, smoke, the live API test and stop passed with the setting, and `GET /halogen/handles` listed the kept `auto` states. Up to four states are kept, using about 0.9 GiB of host memory plus the pool positions they hold, at most half the pool. The startup template check reports the model's own reply as reusable in 4 of its 6 turn shapes, so some reply shapes may still be processed again. A real Pi session with the setting was not measured. Kept states are shared by every client of the port, which stays bound to localhost.

### NPU host setup

XRT was installed from the CachyOS repositories: `xrt 1:2.21.75-14.1` and `xrt-plugin-amdxdna 1:2.21.75-2.1`. Halogen names AMD's XRT 2.25 and Ubuntu's 2.21 as tested, not Arch builds. Checked before installing, the three libraries the container loads need at most `GLIBC_2.38` and `GLIBCXX_3.4.32`, within the image's glibc 2.41 and `GLIBCXX_3.4.33`, and their other dependencies are in the image. The image itself carries no XRT.

Halogen's `halogen-fabric-clock` script was taken from its `v0.18.3` tag (`deploy/host/halogen-fabric-clock`, SHA-256 `0dbd47c15f1002e0a8997ec7070e96f3e009125068eab8eccbbd49424a594f5a`). It only sets the GPU's `power_dpm_force_performance_level` to `manual` and `pp_dpm_fclk` to its top level, 2000 MHz here, or sets the level back to `auto`. Halogen says holding costs about a watt. Idle package power (`amdgpu` `PPT`, which includes the CPU), averaged over 60 seconds after 10 seconds of settling, measured 16.21 W held against 13.56 W on `auto`, then 15.35 W against 13.36 W: about 2.3 W. The boot unit was therefore not enabled; `bin/run.sh` holds the clock only while Halogen runs NPU models, through a sudoers rule limited to `hold` and `release`.

### First NPU run

The first start with NPU models exited because the container could lock only 8 MiB and the small set needs 5.2 GiB. The desktop session inherits `LimitMEMLOCK=8M` from `user@1000.service`, which also capped the launcher's `--ulimit memlock=-1:-1`. A drop-in at `/etc/systemd/system/user@1000.service.d/memlock.conf` raised it to 32 GiB, effective after a reboot. The launcher now refuses NPU models below 4 GiB, because `--rm` discards the container's own error.

Halogen 0.18.3 then started at native 262144 context with each set below, accepted the host XRT libraries and the held clock, checked every NPU file against its record and listed the NPU models in `/v1/models`. The Flash allocation stayed 81.4 GiB. `bin/run.sh halogen stop` released the clock, GTT returned to 0.5 GiB and locked memory to 0.1 GiB. A start without `NPU_MODELS` left the clock on `auto`. The kernel log showed no `amdxdna` errors. Requests came from [`.scratch/npu/routes.py`](../.scratch/npu/routes.py).

| Set | Host RAM used beyond Halogen without NPU | Route checks |
|---|---|---|
| `decider-0.8b`, `embeddinggemma-2`, `qwen3guard-stream-0.6b` | about 6.2 GiB, 3.4 GiB of it locked | Spam decision yes 0.992 in 0.58 s on the first call. `/v1/systemone` picked billing 0.994 in 0.11 s. Text embeddings, 768 dimensions, scored a related pair 0.87 and an unrelated one 0.60 in 0.15 s. A solid red image was closer to "a plain red picture" than to blue, 0.72 against 0.62. The streaming guard labelled the user message and six reply chunks and sent its end summary. |
| `decider-4b`, `wemm-embedding-4b` | about 8.9 GiB, 8.8 GiB of it locked | Spam decision yes 0.987 in 1.65 s. Text embeddings, 2560 dimensions, related 0.72 and unrelated 0.14. Red image closer to red, 0.44 against 0.31. Times are first calls. |

Host RAM was compared as `free` used after the route checks against a start without NPU models. Halogen's own "host memory left" figure barely changed with NPU models (37.6 and 38.1 against 38.7 GiB), so it does not show their cost.

[`.scratch/npu/slowdown.py`](../.scratch/npu/slowdown.py) alternates an uncached 26,150-token Flash prompt with a 1,024-token greedy reply, thinking off, with the NPU idle and while another client keeps it busy:

| NPU load | Rounds | NPU requests per Flash run | Flash prefill | Flash decode |
|---|---|---|---|---|
| idle | 9 | | 1,659 to 1,677 tok/s | 72.0 to 72.3 tok/s |
| `embeddinggemma-2`, 8 short texts per request | 3 | 97 to 101 | 1,624 to 1,631 (about -2%) | 68.5 to 68.8 (about -5%) |
| `decider-0.8b`, 1,500-token text | 3 | 103 to 104 | 1,609 to 1,612 (about -4%) | 67.4 to 67.5 (about -7%) |
| `decider-4b`, same text | 2 | 28 | 1,570 to 1,571 (about -6%) | 64.1 to 64.6 (about -11%) |
| `wemm-embedding-4b`, 8 short texts | 1 | 22 | 1,546 (about -7%) | 63.6 (about -12%) |

These are worst cases: the NPU never rested. Occasional helper requests cost proportionally less. Not exercised: loading both sets at once, audio embeddings, larger images, NPU memory contention between `embeddinggemma-2` and `wemm-embedding-4b`, the guard on a flagged reply, and agent or Pi workloads.

## October 12 update

`bin/update.sh` pulled the new Halogen and Gufo images by digest and atomically updated their image and version pins. Strixite `latest` still resolves to the pinned 0.2.4 digest. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.0 | 0.18.1 | `sha256:f0b39c8908f9897f27ab0a64e964c775e136a7cf7a1bafeb4de0c6d5d1e07e29` |
| Gufo | 0.12.0 | 0.13.0 | `sha256:e03e006da8485314e2440acbce5167c4659ef853af64ed339337f29fe43bd3b4` |
| Strixite | 0.2.4 | 0.2.4 | `sha256:23411d0de807055c97ce885b0ac60cfe17609836bb0d5a5c39d3cbb891a34876` |

Halogen 0.18.1 passed a short check at a reduced 32768 context, described below. Gufo 0.13.0 has not been started on this host: its health, generation, tools, cancellation, metrics, stop and memory release are all unexercised. Everything from the October 11 update onward describes the previous images and must not be read as results for these pins. Unless a point below says it was checked, it comes from the publishers' release notes only.

- **Halogen disconnect handling:** a reply now pauses for 20 seconds when its client disconnects, instead of stopping, and resumes if the same request is retried. `HALOGEN_RETRY_GRACE_S=0` restores the previous behavior. The launcher does not set it, keeping the upstream default. Checked locally: a paused reply keeps `/health` `in_flight` at 1 for the full 20.0 seconds when nothing else arrives, and a new request sent during the pause took the slot and answered in 0.15 seconds. The 20-second bound in `tests/live.py` therefore failed on this release and is now 30 seconds.
- **Halogen scheduling:** a short request now runs between pieces of a long prompt, and a request from a person goes ahead of queued agent turns. The Flash checkpoint is explicitly unchanged, and temperature 0 output is stated to stay byte-identical to serial greedy decode.
- **Halogen additions left off:** `prompt_cache_policy: "no_store"`, structured output above temperature 0 and the opt-in Claude Code sessions (`HALOGEN_FORK`, `HALOGEN_FORK_MAP`) are not used by the launcher or the Pi profile. The `/v1/messages` output-cap and `/v1/responses` history fixes do not touch the Chat Completions route Pi uses.
- **Gufo stall handling:** the server now exits as `device_lost` when generation stops making progress. A stall therefore ends the container instead of leaving it hung. How the launcher's status, logs and the dashboard present that exit is unverified.
- **Gufo fixes:** compatibility routes accept a boolean or null `stream`, and raw completion routes honor `cache_prompt`. The documented 128 n-gram readers for Qwen Flash are a publisher performance change, not benchmarked locally.
- **Cache compatibility:** neither release note mentions a cache or snapshot format change. Whether existing prompt caches are reused or start cold was not checked.
- **Image revisions:** Halogen advertises `b540030f8abf` and Gufo `fcf8bf706f31da3d5c79a3a7da402354cde308a7`. Neither was compared with public source.

### Halogen 0.18.1 check

Halogen was started alone with `CONTEXT=32768` rather than the native 262144, because other applications held about 25 GiB of host RAM. A fresh temporary cache kept synthetic requests out of the normal conversation cache and was removed afterward. Monitoring was not running.

| Check | Halogen 0.18.1, 32768 context |
|---|---|
| Ready, MTP on, API and engine both report 0.18.1 | Pass, engine listening after 34 seconds |
| Bounded non-thinking `ready` generation | Pass |
| Multi-turn recall | Pass |
| Forced named tool | Pass |
| Automatic streamed tool, strict assembled JSON | Pass, 4 fragments |
| Short decode disconnect and generation afterward | Pass with the 30-second bound; slot read idle at 20.0 seconds |
| Native metrics endpoint | Answers; all 28 allowlisted metric names are still exported |
| Stop and host memory release | Pass |

Halogen reported 27.4 GiB of host memory left at this context. After the stop, MemAvailable returned to about 103 GiB, above its pre-start reading, and kernel GTT to about 2.5 GiB, its level with the other applications open. About 3.9 GiB of other processes' memory was in swap afterward.

Not exercised on 0.18.1: native 262144 startup and its allocation, a Prometheus scrape through the monitoring stack, dashboard rendering, metric wire types and semantics, prompt-cache reuse from the normal cache, retry resumption of a paused reply, the new scheduling under concurrent load, and any Pi session. The endpoint also exports `halogen:build_info`, `halogen:structured_requests_total`, `halogen:draft_list_tokens_total` and `halogen:draft_list_misses_total`, which the allowlist drops; whether these are new in 0.18.1 was not checked.

### Image cleanup

The superseded Halogen 0.18.0 and Gufo 0.12.0 images were removed by ID without force. No containers existed. Rolling back requires pulling the previous digests in the October 11 table again.

Sources: [Halogen 0.18.1 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.1/CHANGELOG.md) and [Gufo 0.13.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.13.0).

## October 11 update

All three upstream images were pulled by digest through `bin/update.sh`, and image and version pins were atomically updated. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged. Basic checks passed one engine at a time with native 262144 context and MTP enabled. All engines and monitoring are stopped afterward.

| Engine | Previous | Selected | Selected image digest |
|---|---|---|---|
| Halogen | 0.17.5 | 0.18.0 | `sha256:de3b47d2e5f24f98a38ba5fb66b0075b0cd8a3219c38917c78fb4bbeb42b88d9` |
| Gufo | 0.11.0 | 0.12.0 | `sha256:25c52218f494f9c35fab96184b813576d4f1e71cbe025631b106360a1d420206` |
| Strixite | 0.2.3 | 0.2.4 | `sha256:23411d0de807055c97ce885b0ac60cfe17609836bb0d5a5c39d3cbb891a34876` |

## Local adaptations

No launcher or Pi-profile migration was required. Existing localhost endpoints, supported thinking choices, sampling settings, read-only model mounts, separate caches and single-engine startup lock remain appropriate. New speech, vision, named-session and Messages features were not enabled.

`tests/live.py` now also checks an automatic streamed tool call for Halogen and Gufo, assembling argument deltas by tool index and requiring strict JSON, a successful tool-call finish and stream completion. It never executes returned calls. The existing named-tool requirement and 20-second decode-disconnect assertion remain intact. This covers Gufo's changed incremental argument delivery without a lengthy coding test. Dashboard version descriptions were refreshed; existing queries and metric allowlists remain unchanged.

### Halogen

The release fixes cache reuse when clients change or drop part of the newest message, including disk cut-back instead of writing another conversation copy. The Flash checkpoint is explicitly unchanged. Disk state uses separate engine-build namespaces, so an upgrade starts cold while previous namespaces remain on disk. The 16 GiB limit applies to the active namespace, not the whole cache directory. Normal caches were not pruned or rotated.

The new scalar counters `halogen:cache_last_message_rewrites_total` and `halogen:cache_disk_cut_back_total` were verified as counters on the real endpoint. They count resumed rewrite requests and disk cut-back events respectively, not bytes saved. Both were zero in this short check. Existing allowlists intentionally drop these optional additions; the current dashboard remains compatible without new panels.

The image advertises revision `c31448922f6e`, which was not resolvable in the public source repository during review. Public v0.18.0 resolves to `9b12eadaef73475aa77ec82122474690707c92b6`. Public release documentation and the actual image's version, health, metrics and generation were checked, but source equivalence to the advertised binary revision is not established.

### Gufo

Native tool arguments now stream incrementally. Pi already assembles OpenAI tool deltas, so no profile change was necessary. The new Flash-Next continuation adapter is not yet attached to HTTP serving; the legacy serving cache identity and snapshot payload version remain unchanged. Existing same-settings snapshots are structurally compatible, but cross-version restoration was not tested.

Snapshot capture now preserves HIP headroom and can fall back to already-budgeted host payloads. This is not a new memory-limit flag or a guarantee against host memory pressure. Retain the conservative 2 GiB RAM-cache and disk-staging limits. Upstream recommends 8 GiB staging for full-depth MTP snapshots if RAM permits. Larger budgets and full-depth restart persistence remain separate, deferred memory-policy work. Serving native context does not require changing those limits.

### Strixite

The release defaults to seven MTP drafts instead of five. Think-close-on-call is on independently of our disabled thinking nudge: it can inject a thinking closure before a tool call begun inside reasoning. This is a serving-policy change, not a replacement for strict tool-argument validation or the test sandbox. Historical coding comparisons used five drafts and no close-on-call intervention; they must not be relabeled as measurements of this release. Publisher speedup claims were not benchmarked locally.

Prefill progress is opt-in through `return_progress: true`. The Pi profile does not request it, and Pi progress rendering was not evaluated. Disk cache format and state fingerprints remain compatible with the unchanged model, MTP and YaRN baseline. Eviction writes release RAM progressively. No cache rotation is required by the source changes, and successful restoration remains unvalidated.

The real endpoint exports the additive scalar counter `strix_think_closed_for_call_total`, zero in this non-thinking API check. Existing metrics keep their accounting semantics. The current allowlist intentionally drops this optional counter. No dashboard query migration is needed.

## Basic runtime checks

Fresh temporary SSD caches kept synthetic requests out of the normal conversation caches. The model presence and size check ran at launch. The previously completed full weight hashes were not repeated. The optional existing monitoring stack ran during the checks.

| Check | Halogen 0.18.0 | Gufo 0.12.0 | Strixite 0.2.4 |
|---|---|---|---|
| Ready, native 262144, MTP on | Pass | Pass | Pass, YaRN 1 and no degradation |
| Bounded non-thinking `ready` generation | Pass | Pass | Pass |
| Multi-turn recall | Pass | Pass | Pass |
| Forced named tool | Pass | Pass | Unsupported, unchanged |
| Automatic streamed tool, strict assembled JSON | Pass, 4 fragments | Pass, 4 fragments | Pass, 22 literal-tag argument fragments |
| Short decode disconnect and generation afterward | Pass, within existing 20-second bound | Pass, within existing 20-second bound | Pass, 0.253 seconds |
| Native Prometheus scrape | Pass | Pass | Pass |
| Independent readiness probe | Not configured | Pass | Pass |
| Stop and host memory-release gate | Pass | Pass | Pass |

Strixite also passed its existing automatic tool-result follow-up and deliberate 12-token truncation inspection. The incomplete arguments were not repaired or executed. Halogen reported 81.4 GiB startup allocation, Gufo 88.48 GiB GPU allocation. These are historical startup reports, not workload peaks or additive host-memory measurements. After every stop, MemAvailable returned to approximately 119 GiB and kernel GTT to approximately 0.64 GiB before the next engine started.

At the user's request, no Pi coding loop, coding matrix, long-context request, benchmark, deep-prefill cancellation, cache-restoration test, GPU-fault test or new-feature exercise was run. The thinking-enabled Strixite close-on-call intervention was source-reviewed, not deliberately triggered. Older coding and monitoring-overhead results remain historical. Short successful operation does not establish near-capacity memory safety or unrestricted real-project tool safety.

## Podman cleanup

After successful checks and shutdown, removed the three superseded engine images, unused browser build branches and intermediates and the hello-world image. In total 23 image records were removed without force. Podman's reported shared image-store size fell from 17.62 GB to 13.66 GB, approximately 3.96 GB reclaimed. No stopped containers existed before the update, and test and monitoring containers were auto-removed on stop. Zero containers remain.

All seven current engine and monitoring pins remain locally available. The maintained Pi browser image and its required base/ancestor images remain, for 18 total image records including build ancestry. Named monitoring volumes, normal conversation caches and weights were retained. Do not blanket-prune untagged images. Digest-pinned current images also appear untagged and reclaimable. Rolling back now requires pulling the previous digest again.

## Sources

- [Halogen 0.18.0 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.0/CHANGELOG.md), [cache namespaces](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.0/README.md#L2183-L2228) and [new counters](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.0/README.md#L559-L576).
- [Gufo 0.12.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.12.0), [continuation adapter scope](https://github.com/gufo-org/gufo/blob/v0.12.0/docs/models/qwen3.8-flash-next/CONTINUATION-ADAPTER.md) and [snapshot staging](https://github.com/gufo-org/gufo/blob/v0.12.0/docs/SERVER.md#L218-L233).
- [Strixite 0.2.4 release](https://github.com/shawnshekari/strixite/releases/tag/v0.2.4), [exact source comparison](https://github.com/shawnshekari/strixite/compare/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6...06e45551558b1d541c59c831041f7a52468d2c52) and [close-on-call implementation](https://github.com/shawnshekari/strixite/blob/06e45551558b1d541c59c831041f7a52468d2c52/serve/engine.cpp#L510-L539).
