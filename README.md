# Strix Halo inference

Run and compare Qwen3.8-Flash-Next with Halogen Flash and Gufo on a Ryzen AI Max+ 395, Radeon 8060S (`gfx1151`), and 128 GiB shared memory under CachyOS. Strixite is a provisioned third-engine trial with native-256K startup, short API tools and cancellation, and guarded synthetic Pi loops validated. Long-context workloads and unrestricted real-project use remain unvalidated.

Separate rootless Podman launchers with digest-pinned upstream images and revision-pinned, SHA-256-verified model downloads. Halogen and Gufo have passed local generation and lifecycle checks with the full native 256K context configured, plus a 40,030-token prompt that exceeds the old 32K limit. Near-capacity prompts remain untested. All 13 selected Halogen and Gufo model files passed a full post-download integrity check. No engine starts automatically at login.

- [Engine research and sources](docs/qwen3.8-engine-research.md), checked October 10, 2026.
- [Strixite third-engine assessment](docs/strixite-research.md), with container compatibility, 256K memory estimates and performance evidence. See the [trial operations, local allocation results and remaining validation gates](docs/strixite.md).
- [Podman setup patterns from the existing toolbox](docs/podman-reference.md).
- [Local validation results and limitations](docs/validation.md).
- [Engine updates](docs/engine-updates.md), with the October 12 pins and their partial checks, the October 11 release compatibility and basic runtime checks, and image cleanup.
- [Pi coding agent setup for all three engines](docs/pi.md), including model-card sampling, thinking controls and 256K compaction settings.
- [Medium versus xhigh for routine coding](docs/thinking-comparison.md), with local exploratory results and a repeatable Pi comparison.
- [Sandboxed three-engine coding comparison](docs/coding-comparison.md), with matched tasks, strict tool arguments, memory-release checks and a repeatable smoke gate.
- [Optional single-page monitoring dashboard](docs/monitoring.md), with independently containerized collection, bounded history and explicit memory-accounting caveats.
- [Halogen inference telemetry](docs/halogen-monitoring.md), with native token, processing-speed, pool, cache and speculation readings.
- [Gufo inference telemetry](docs/gufo-monitoring.md), with independent readiness probing, live token progress and explicit engine-specific accounting.
- [Strixite inference telemetry](docs/strixite-monitoring.md), with independent health probing, completion-accounted rates, cache pressure and explicit historical-speed semantics.
- [Halogen upstream](https://github.com/peonist-ai/halogen-flash-server).
- [Gufo upstream](https://github.com/gufo-org/gufo).

## First run

Requirements: Linux with accessible `/dev/kfd` and `/dev/dri`, rootless Podman, Bash, curl, Python 3, coreutils and `flock`. Model downloads need approximately 216 GiB in total, plus images, partial downloads and prompt caches. Existing model files are never deliberately overwritten. Halogen is a proprietary binary engine with a [free-use EULA](https://github.com/peonist-ai/halogen-flash-server/blob/main/LICENSE.md). Model licenses apply separately.

Run from this checkout. Launcher commands take the engine first, then the action. Old action-first commands are rejected with a migration hint. Pull and diagnose each engine before downloading:

```bash
bin/run.sh halogen pull
bin/run.sh halogen diagnose
bin/run.sh gufo pull
bin/run.sh gufo diagnose
```

The current images are Halogen 0.18.3, Gufo 0.15.0 and Strixite 0.2.4, pinned on October 14 and not started on this host yet. Halogen 0.18.1 passed generation, API tools, short decode cancellation and shutdown checks at a reduced 32K context only; Gufo 0.13.0 was never started on this host. Strixite 0.2.4 and the previous Halogen 0.18.0 and Gufo 0.12.0 passed basic native-256K generation, API tools, short decode cancellation and shutdown checks on October 11. Earlier detailed coding and monitoring measurements used older versions; see the [update record](docs/engine-updates.md) for scope. `config/pins.env` records the current immutable image digests, release versions and model revisions. `config/*-files.tsv` records SHA-256, byte size and relative path for each selected file. Downloads use curl, resume `.partial` files and validate hashes before promoting them to final filenames. Downloading a whole upstream repository would fetch unnecessary alternative quantizations, so these manifests select only the required files.

```bash
bin/models.sh download halogen
bin/models.sh download gufo
```

Downloads can take a long time. Repeating the command verifies existing final files and resumes incomplete files. A size or checksum mismatch fails without replacing the existing file. `bin/models.sh verify ENGINE` performs a full hash check. Launches use `check`, a fast presence and size check, rather than reading hundreds of gigabytes before every start.

NPU model files for Halogen are listed in `config/npu-files.tsv` and stored under `/home/bogdan/models/npu`, the layout Halogen reads at `/models/npu`. `bin/npu-manifest.sh` derives the list from the record inside the pinned Halogen image, which Halogen uses to refuse any other file. Rerun it after a Halogen pin change, review the diff, then run `bin/models.sh download npu`. The files are downloaded but not loaded; see the [NPU plan](.scratch/npu/spec.md).

Start one engine, wait for its readiness endpoint, then test and stop it:

```bash
bin/run.sh halogen start
bin/run.sh halogen logs
bin/run.sh halogen status
bin/run.sh halogen smoke
python tests/live.py halogen
bin/run.sh halogen stop

env SPECULATIVE=off bin/run.sh gufo start
bin/run.sh gufo logs
bin/run.sh gufo status
bin/run.sh gufo smoke
python tests/live.py gufo
bin/run.sh gufo stop
```

`start` launches a detached container, not a readiness guarantee. `status` returns nonzero until the service is ready. Check logs after failure. Gufo uses `/ready`, not just its liveness endpoint. A running managed engine blocks another start. `stop` allows 60 seconds for shutdown and prints host memory afterward. Containers are removed on exit, while model files and prompt caches remain.

Strixite uses the same engine-first CLI, for example `bin/run.sh strixite start --wait`, with `/health` at localhost:5300 and a 90-second stop timeout. Its baseline explicitly selects native 262144 capacity, YaRN factor 1, MTP on, thinking nudge off, fail-on-low-memory behavior and a separate cache. The pinned image is pulled and all six files in its approximately 114.1 GiB package are fully hash-verified. Initial startup reported 84.6 GiB GPU buffers and 29.3 GiB post-load MemAvailable, with successful readiness, a bounded `ready` reply and shutdown with memory release. Separate short API tool and disconnect checks passed, followed by filesystem-sandboxed Pi read/edit/bash loops with thinking off and medium and a strict streamed-JSON guard. Follow [the trial guide](docs/strixite.md), not the existing engines' forced-tool live test. The shared Pi profiles include Strixite, installed on this host, with only supported levels and neutral penalties. Normal Pi tools are not sandboxed by provider configuration. Its telemetry appears on the optional monitoring dashboard. These checks do not validate unrestricted real-project use, deep-prefill cancellation or near-capacity workloads.

Use `bin/run.sh halogen start --wait` to wait for readiness and print the endpoint and Pi launch command. Replace `halogen` with `gufo` for that engine. Waiting defaults to 300 seconds, adjustable with `START_TIMEOUT=1..3600`. Individual readiness probes are capped at five seconds. Container exit or timeout fails visibly. Timeout or interruption stops only the wait, leaving any running container available for inspection. Check logs or explicitly stop it before retrying. The startup lock is released after container creation, before waiting.

`bin/run.sh halogen logs` prints the last 100 log lines and exits. Use `bin/run.sh halogen logs --follow` for recent output followed by live server logs. Replace `halogen` with `gufo` for that engine. Pressing `Ctrl+C` stops only the viewer, not inference. Following ends when the container exits. Auto-removed containers have no retained Podman logs, so inspect logs before stopping when needed. There is no foreground-start option.

`bin/run.sh halogen status` summarizes the actual container's image identity and OCI version, context, speculation, cache limits and readiness. Current pins and shell overrides do not redefine a running container's configuration. Cache disk usage comes from `du` over the entire mounted cache directory, including records for other configurations, and is not the active engine's retained-cache counter. RAM cache usage is unavailable unless verified telemetry is added. Allocation figures extracted from recent startup logs are labeled historical, not live. They may become unavailable when startup lines fall outside the last 1,000 log lines. Host RAM and swap come from `/proc/meminfo`; GTT comes from each GPU's sysfs counters and includes other GPU users. These are separate accounting views, not additive estimates of free memory. In particular, Halogen's pinned weights can make `MemAvailable` misleading. Status remains nonzero for missing, stopped, paused, starting or unresponsive engines. Inspection, disk usage, log collection and readiness probes have finite timeouts. The monitoring dashboard is not required.

The default is one active request with the full native 262,144-token capacity, commonly called 256K. MTP is on by default. After verifying Gufo's autoregressive path, start it normally to enable its matching shared Q8 draft head. Use `env SPECULATIVE=off` to disable speculation in either engine, or `env CONTEXT=32768` to reduce capacity for a smaller-memory run. Context must be between 1,024 and 262,144 tokens. Update Pi's matching `contextWindow` if you override capacity. Changing the launcher does not resize an already running container or update your live Pi configuration. Stop and restart the engine, then explicitly update the client. Vision is not enabled in this initial setup.

## Optional dashboard

Start the independently managed Prometheus, node-exporter and blackbox-exporter containers:

```bash
bin/monitor.sh pull
bin/monitor.sh start
bin/monitor.sh status
```

Open the printed `file://` address of [the dashboard page](config/monitoring/dashboard.html) in a browser. One page shows live CPU, RAM, swap, GTT, memory pressure, disk activity and accessible GPU sensors, followed by the running engine's inference metrics with explicit engine-specific reporting limits. Choose a refresh interval of 1, 2, 5, 10, 15 or 30 seconds in its header; the default is 2 seconds, matching the scrape interval. Gufo and Strixite readiness use the official blackbox-exporter; stop and restart an existing stack to load new scrape/probe configuration. Use `pull` first only if a pinned monitoring image is missing or changed. Use `bin/monitor.sh prometheus logs --follow` for logs and `bin/monitor.sh stop` to stop only monitoring. All services listen on loopback. History survives restart with seven-day and 2 GiB size-based retention. See [monitoring setup and limits](docs/monitoring.md) for permissions, measured overhead and cleanup. Inference remains usable without the dashboard.

For start, stop and log controls on the page, run `bin/dashboard.py` instead and open the `http://127.0.0.1:9099/` address it prints. The page then has buttons to start and stop monitoring and one engine at a time, and a drawer that follows container logs. The helper runs in the foreground, listens on loopback only and can run nothing except those fixed `bin/run.sh` and `bin/monitor.sh` commands. See [dashboard controls](docs/monitoring.md#dashboard-controls) for its boundaries.

## Update engine images

`bin/update.sh` checks all three publishers' `latest` image tags, validates stable release versions and Linux AMD64 metadata, pulls changed images by their resolved digests, then atomically updates the image and version pins in `config/pins.env`. It refuses version downgrades and writes none of the pins if any pull fails. Previously pulled images remain available. Updating requires Skopeo in addition to the ordinary launcher requirements. Skopeo is already installed on the validated host.

The updater includes Strixite and normalizes an optional leading `v` in OCI release versions before comparison and pinning. Model revisions are never changed implicitly. The October 11 update selected Halogen 0.18.0, Gufo 0.12.0 and Strixite 0.2.4, followed by [basic runtime checks](docs/engine-updates.md). The October 12 update moved Halogen to 0.18.1, checked briefly at 32K context, and Gufo to 0.13.0, not started yet. The October 14 update moved Halogen to 0.18.3 and Gufo to 0.15.0, and neither has been started yet.

```bash
bin/update.sh --check   # Inspect available images and release notes without changing anything
bin/update.sh           # Pull changed images and update all three pins
bin/update.sh --pull    # Pull all resolved images even if their pins are already current
```

The output shows versions, digests, advertised image revisions and the release notes of every stable version after the current pin up to the one being selected, oldest first, so a jump over several releases also shows the ones it skipped. Gufo and Strixite use their GitHub Releases pages. Halogen currently publishes no GitHub Releases, so the updater explicitly uses the matching version section from its tagged `CHANGELOG.md`. Notes are shown even when the pins are current. Missing notes are reported without substituting a different release. GitHub rate-limit or other HTTP failures, including the tag lookup, abort the update before pulls and pin changes.

This tracks published stable images, not every commit on `main` or the `edge` tag. Release notes are publisher claims, not local validation results. Review them for model-format and runtime compatibility before restarting. The script does not rebuild source, execute the new images, upgrade model revisions, download weights, alter Pi settings or restart an active container. There is no `--build` flag because these are prebuilt upstream images. Content-addressed layers do not need a global cache prune to fetch a newer image.

To use an updated pin, finish the current request, then explicitly restart one engine and verify it:

```bash
bin/run.sh halogen stop
bin/run.sh halogen start
bin/run.sh halogen status
bin/run.sh halogen smoke
```

Use `gufo` or `strixite` instead for that engine. An image update leaves the currently running container on its existing image until you restart it. Repeat `status` until ready. Run `python tests/live.py ENGINE` for Halogen/Gufo or `python tests/strixite_live.py` for Strixite after a release change to verify conversation, tools and cancellation before relying on it for coding.

For a deliberately fresh prompt cache, stop all managed engines first and run `bin/update.sh --fresh-cache`. This archives only the `halogen`, `gufo` and `strixite` cache directories under the launcher's `CACHE_ROOT`, normally `$HOME/.cache/strix-halo-inference`, into a timestamped sibling archive. The next start creates an empty engine cache. A shared startup lock prevents a managed engine from starting during rotation. Old data is preserved, not deleted, so archives still consume disk space and may contain private conversation state. No weights, unrelated Podman caches or host page caches are cleared. This command also performs the ordinary image update, so review `--check` first. `--check` cannot be combined with `--pull` or `--fresh-cache`.

Review updates with `git diff -- config/pins.env`. To roll back, restore the previous image and version assignments together, pull that digest if it was removed during cleanup, then explicitly restart the selected engine. Do not restore the entire file if it contains unrelated model-pin edits you want to keep. Digest-only current images can appear untagged and reclaimable in Podman; do not use blanket image pruning to clean this setup. Preserve every current engine and monitoring pin.

## Container boundaries

- Separate rootless Podman containers, using upstream images where practical.
- Images and model revisions are pinned in versioned configuration. No moving `latest` tags or review builds are used.
- Start with manual launches. Add user-level systemd Quadlets after both engines work reliably. Do not enable both at login.
- Run only one engine at a time. Separate containers do not create additional GPU memory, and both engines need most of the host's shared memory.
- Publish Halogen at `127.0.0.1:8731` and Gufo at `127.0.0.1:8080`, subject to checking for existing listeners. Do not expose internal engine ports.
- Pass `/dev/kfd`, `/dev/dri` and the NPU's `/dev/accel/accel0` to every engine. The NPU device is world-readable and writable on this host, so it needs no group. None of the engines uses the NPU yet; see the [NPU plan](.scratch/npu/spec.md). With `crun`, preserve supplementary GPU groups. This host's `runc` path was verified with directly accessible GPU devices. If devices require group-based access and the container cannot access them, use `crun` rather than changing device permissions.
- Halogen uses its documented host IPC setting. Both launchers request unlimited container memlock, but rootless Podman can silently clamp this to the host user's hard limit. On this host it remains 8 MiB. The GPU-backed weight allocation still worked. Optional Halogen `mlock` and NPU features are not enabled. No seccomp disablement, privileged mode or writable host control mount is used.
- Keep existing BIOS, kernel and IOMMU settings for the first baseline. Investigate any required host tuning explicitly rather than applying it silently.

## Model storage

`/home/bogdan/models` is the central host directory. It is not part of this repository and must be bind mounted into each inference container at `/models`. Use a read-only mount during inference:

```text
/home/bogdan/models:/models:ro
```

Use the existing publisher/model directory convention:

```text
/home/bogdan/models/
  peonist-ai/halogen-qwen3.8-flash-next/  # Halogen native checkpoint and lookup table
  unsloth/Qwen3.8-Flash-Next-GGUF/       # Gufo target, shared MTP head, optional projector
  wemoh/Qwen3.8-Flash-Next-strixw/       # Strixite trial weights, n-gram table and tokenizer
```

Downloads happen on the host before inference. The inference containers receive no automatic-download setting and mount the entire central directory read-only. Download locks are per model repository, so separate package downloads can run independently without two writers touching the same files. Override the host root with `MODELS_DIR` only when deliberately using another central store.

Generated prompt caches live under `$HOME/.cache/strix-halo-inference/halogen` and `$HOME/.cache/strix-halo-inference/gufo`, each mounted writable at `/cache`. Override their parent with `CACHE_ROOT`. Disk caches are capped at 16 GiB per engine for the active configuration. Gufo additionally caps retained RAM snapshots and disk staging at 2 GiB each. These caches contain conversation state and must not be committed or shared between engines.

Strixite creates its own `$HOME/.cache/strix-halo-inference/strixite` on first start, with a 16 GiB disk cap and an 8 GiB MemAvailable margin for retained RAM state. That margin is not a RAM-cache cap or a memory reservation. Its model store remains read-only, with all prompt state directed to `/cache`.

Pre-existing empty directories and four `.ini` files under `/home/bogdan/models` are untouched. Only the selected Halogen, Gufo and Strixite repositories have received downloads.

## Checks and remaining work

The Halogen/Gufo coding comparison and Strixite Pi tool check share a fail-closed Bubblewrap filesystem and process sandbox. Model-driven Pi tools and independent acceptance code see only the current writable synthetic workspace, immutable temporary settings and read-only software. They cannot access live Pi files, host projects, models, engine caches or GPU devices. Host networking is shared for localhost inference, not sandboxed. See [comparison operation and isolation](docs/thinking-comparison.md) and [Strixite test scope](docs/strixite.md). With the existing Bubblewrap and Homebrew installation, `PYTHONDONTWRITEBYTECODE=1 python tests/pi_sandbox.py` checks the real boundary without inference.

```bash
bash -c 'for file in bin/*.sh tests/*.sh; do bash -n "$file" || exit; done'
shellcheck -x -P SCRIPTDIR bin/*.sh tests/*.sh
tests/models.sh
tests/update.sh
python tests/run.py
python tests/status.py
PYTHONDONTWRITEBYTECODE=1 python tests/monitor.py
PYTHONDONTWRITEBYTECODE=1 python tests/dashboard.py
PYTHONDONTWRITEBYTECODE=1 python tests/strixite_metrics.py
```

The offline model test verifies refusal to overwrite a corrupt, size-correct model file and rejection of missing weights. The offline update test checks all-or-nothing pin changes on pull failure, correct release-section selection, refusal to rotate caches with an active engine, archive preservation and version-downgrade refusal. Its CLI stubs test project policy, not external provider compatibility. `tests/live.py ENGINE` requires a running model and verifies multi-turn recall, forced tool arguments, streaming disconnect slot release and generation after cancellation. It does not run during ordinary offline checks.

Both packages are downloaded and fully hash-verified. Gufo passed autoregressive and MTP validation, with identical greedy text on two comparison prompts. Both engines pass readiness, generation and lifecycle checks at the default 256K allocation. Next, compare matched prompts using the same power profile, sampling and thinking settings, including near-capacity prompts. Record generation quality, cold prompt processing, follow-up latency and memory pressure. Different weight formats make this a practical setup comparison, not a pure engine benchmark. Restart-safe disk restoration, near-capacity workloads and multi-request serving still need validation before adding Quadlets.

Large models can leave little memory for the desktop and other applications. Do not treat successful startup as proof that full context or multiple sessions will fit safely.
