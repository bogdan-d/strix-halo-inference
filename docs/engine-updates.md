# Engine updates, October 11, 2026

All three upstream images were pulled by digest through `bin/update.sh`, and image and version pins were atomically updated. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged. Basic checks passed one engine at a time with native 262144 context and MTP enabled. All engines and monitoring are stopped afterward.

| Engine | Previous | Current | Current image digest |
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
