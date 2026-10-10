# Optimization ideas

Initial thoughts, not a spec or implementation tickets. No runtime changes are approved by this note. Command examples below describe proposed behavior unless explicitly marked as current.

## Engine-first commands

Change `bin/run.sh` to take the engine before the action. Keeping the engine fixed makes it easier to edit the previous shell command when switching between start, status, logs and stop.

```bash
bin/run.sh halogen start
bin/run.sh halogen status
bin/run.sh halogen logs
bin/run.sh halogen stop
bin/run.sh gufo start
```

Apply the same order to every launcher action. Update usage output, printed next-step commands, docs and any callers together. Still undecided whether to reject the old action-first syntax immediately or support it temporarily.

## Live monitoring with Grafana

Add an optional, separately containerized Grafana setup in this repo. Keep it independent of inference so an engine can run without monitoring. Use the supplied dashboard screenshot as visual inspiration, not as evidence that either engine exposes all the metrics shown.

Useful dashboard panels:

- Inference: decode and prefill tokens per second, generated token totals, context usage, cache behavior and speculative decoding acceptance when available.
- Engine: active backend, readiness, uptime, running requests and queued requests when exposed.
- Host: GPU load, temperature and power, CPU load, disk activity, physical RAM, swap, GTT usage and memory pressure.
- Memory explanation: distinguish engine-reported allocation, kernel memory accounting and estimates of practical headroom. Halogen's pinned weights can make `MemAvailable` misleading. GTT usage alone is not the model's total memory footprint.

Grafana needs a data source, not just an engine URL. A possible starting point is Grafana plus Prometheus, using native engine metrics where available and adding a small collector only for verified gaps. Check what the pinned Halogen and Gufo releases actually expose before choosing exporters or promising panels. Missing metrics should appear as unavailable, not as zero. Keep decode speed distinct from aggregate token throughput.

Keep the dashboard localhost-only, give collectors only the access they need, and avoid exposing the Podman socket or mounting weights just for monitoring. Do not collect prompts, completions or source code. Bound retention and resource usage so monitoring does not compete materially with the model.

Open questions: which metrics are available without modifying engines, how to reach localhost-bound engine endpoints from collectors, which host readings require access, and how much dashboard history is useful. Keep this as a small local setup, not a general observability platform.

## Visible server output

Current behavior: `bin/run.sh start halogen` starts a detached container. `bin/run.sh logs halogen` already exists, but prints only the last 100 lines and exits.

Two possible improvements with the proposed command order:

```bash
bin/run.sh halogen logs --follow
bin/run.sh halogen start --fg
```

Following logs is the smaller change and works for an already-running engine. `Ctrl+C` should stop the log viewer without stopping inference.

For `start --fg`, decide what foreground means before implementing it. An attached container run should have explicit interrupt and shutdown behavior. Starting detached and then following logs is simpler, but it is not the same lifecycle and should be named or documented accordingly. Preserve the startup lock's existing protection without holding it for the entire log-viewing session.

Tentative preference: add log following first. Add a foreground start option only if a single-command startup view is still useful, with explicit behavior on `Ctrl+C`.

## Faster thinking for routine coding

The Pi profiles currently default to `xhigh`. Compare `medium` on straightforward edits while keeping `xhigh` available for difficult debugging and planning. Generating fewer reasoning tokens could save more time than engine-level tuning, but verify coding quality rather than assuming a lower setting is better.

Keep the existing recommended sampling settings during the comparison so only thinking effort changes. Compare total task time and whether the resulting changes pass their checks. This is an experiment, not approval to change the live Pi defaults.

## Wait for readiness during startup

Add an optional `start --wait` using the proposed engine-first command order:

```bash
bin/run.sh halogen start --wait
```

Wait until the selected engine reports readiness instead of treating a started container as a ready model. Fail visibly if the container exits or a bounded startup timeout expires. On success, print the endpoint and matching Pi launch command. Keep this compatible with any future foreground or log-following behavior.

## More useful status output

Make `status` summarize the running image version, readiness, configured context, MTP state and cache size. Distinguish configured cache limits from actual usage. Report the running container's configuration rather than assuming it matches the current pins or shell environment.

Include memory readings only when their source and meaning are clear. Label engine-reported allocation, kernel GTT usage and host memory accounting separately. Show unavailable readings as unavailable rather than zero. This should remain useful without Grafana running.
