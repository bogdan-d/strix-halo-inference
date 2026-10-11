# Strixite third-engine trial

Strixite is integrated into the manual launcher and model downloader, but has not been pulled, provisioned or run on this host. Halogen and Gufo remain the validated engines. This is a controlled third-engine trial, not a replacement or a demonstrated performance upgrade. Read the [suitability assessment](strixite-research.md) and [performance evidence](strixite-performance-research.md) for the remaining risks.

Stage 1 added repository configuration, launch support and offline policy checks only. Image pulls, model downloads and runtime validation require separate approval. No host settings, existing weights or live Pi configuration were changed.

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

## Provision and launch after approval

Recheck upstream compatibility and host free disk space before provisioning. These commands pull or execute an upstream image and download new weights. They are not part of the completed offline integration:

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

## Runtime acceptance gates

Successful 256K allocation is only the first gate. Record actual GPU allocation, MemAvailable, GTT, swap and memory pressure through generation, cache export and shutdown. The approximately 88.6 GiB GPU estimate and approximately 14.8 GiB required post-load MemAvailable are derived from publisher measurements, not local results. Stop on GPU errors or unsafe memory pressure rather than tuning the host automatically.

- Verify health, expected model and native context, then bounded generation. Inspect any degraded settings and confirm the intended startup flags in logs.
- Test automatic tool selection, streamed argument integrity, multi-turn recall and an isolated Pi read, edit and bash loop. Include literal model tags and truncated tool arguments. Do not permit repaired partial JSON to execute commands.
- Measure disconnect cancellation and generation afterward at increasing prompt depth. The inherited 16384-token chunk can delay cancellation to a chunk boundary, reportedly around 25 seconds at depth. Record latency rather than silently relaxing the existing engines' 20-second check.
- Compare MTP and plain greedy output on uncached prompts, then validate clean stop, restart-cache restoration and compatibility after configuration changes.
- Increase realistic coding and retrieval prompts toward native 256K, leaving space for output. Measure quality and peak memory, not just decode speed. Compare matched sampling, thinking, power and cache conditions against the existing engines. Different quantization makes this a practical setup comparison, not a pure engine benchmark.

## Pi and deferred integration

No Strixite Pi provider is installed or added to the existing shared profiles. Readiness output points here instead of printing a command for a nonexistent provider. A future isolated Chat Completions profile should use the loopback endpoint, model `qwen3.8-flash-next`, `contextWindow: 262144` and an initial 16384 output cap. Do not edit live Pi defaults before tool-loop validation.

Strixite accepts ordinary `tool_choice: auto` but rejects named-tool selection and `required`. `tests/live.py` deliberately remains limited to Halogen and Gufo with its forced-tool requirement intact. Strixite needs separate automatic-tool and cancellation validation before real project use. Nonzero presence and frequency penalties are rejected, as is repetition penalty other than 1. In particular, do not copy the existing thinking-off presence penalty 1.5. Thinking-enabled temperature 1, top-p 0.95 and top-k 20 are supported by contract, but Pi behavior is not yet validated.

`bin/update.sh` still updates only Halogen and Gufo and `--fresh-cache` archives only their cache directories. It preserves the Strixite pins and cache. Its active-engine guard also refuses rotation while managed Strixite is running. Until retention is justified, review and change Strixite image and version pins together manually, never changing its model revision implicitly. There is no Strixite Grafana dashboard, persistent service, chat UI, authentication or vision integration.

Offline checks cover launcher isolation, explicit arguments, stop timing, bounded smoke payload, running-container status and refusal to overwrite corrupt model files. They do not establish upstream image, GPU or Pi compatibility. No runtime acceptance gate has been exercised on this host yet.
