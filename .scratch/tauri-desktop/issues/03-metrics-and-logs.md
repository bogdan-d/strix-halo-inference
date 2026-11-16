# 03: Historical metrics, host header and streamed logs

Status: ready-for-agent

Blocked by: [01](01-desktop-shell.md), [02](02-native-controls.md)

Spec: [Tauri desktop port](../spec.md)

## Scope

Port the existing JSDoc-typed page behavior to bundled TypeScript while preserving panel definitions and PromQL semantics. Keep a single panel JSON source compatible with tests/dashboard_panels.py and the three engine metric suites. Preserve ranges, gates, missing-data behavior, counter resets, rate windows and engine-specific meanings.

Retain read-only Prometheus fetches to its fixed loopback origin, with the narrow CSP addition and a real WebKitGTK CORS check. Use a fixed-endpoint native adapter only if needed, not Den’s small raw HTTP client for dozens of chart requests. Add the compact host strip from Den, including CPU / GPU temperatures, bounded graphs and saved display mode, in the same WebView. Keep Halogen’s memory caveat scoped to Halogen.

Preserve streamed logs for all six sources using native subscriptions and Tauri channels. Cancel and reap only owned viewers on drawer/source/renderer/app closure. Bound displayed log bytes as well as entries. Snapshot tail polling is not equivalent and is outside the agreed plan.

## Acceptance criteria

- [ ] Historical host/engine charts retain current panel behavior and the existing panel/promtool tests pass.
- [ ] The native controls and live header work with monitoring off; chart errors/stale data recover when monitoring returns.
- [ ] Refresh/visibility changes cannot overlap polls indefinitely; chart ranges and view preferences persist within the app profile.
- [ ] All six log sources follow live output, keep the drawer’s scroll/follow behavior, and clean up viewers on cancellation and renderer/app exit.
- [ ] Agent inspection can diagnose chart requests and frontend errors; responsive layout is checked with the richer header and active log drawer.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.
