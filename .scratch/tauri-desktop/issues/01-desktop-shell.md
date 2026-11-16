# 01: Desktop shell and agent debugging

Status: resolved

Blocked by: None

Spec: [Tauri desktop port](../spec.md)

## Scope

Create a standalone single-WebView Tauri 2 app using the reusable Den runtime pieces. Give it a separate app ID, icon, single-instance socket, browser profile, window-state file, log and inspector record. Keep desktop data outside the per-engine caches. Port F11 and normal/maximized/fullscreen restore, rotated native logs and the explicit run --inspect workflow. Render bundled local dashboard assets; adapt Den’s build rather than copying its ComfyUI view machinery.

Build only in rootless Podman, using rechecked stable pins. Do not install host compilers or packages. No shared framework crate, remote ComfyUI view, library, job polling, download/media machinery or audio-sink preflight. Leave existing browser shortcuts active until ticket 06.

## Acceptance criteria

- [x] The release app opens the bundled page in one WebView and coexists with Den without sharing identity or storage.
- [x] A second launch focuses the existing app; F11 and normal/maximized/fullscreen restoration work across real restarts.
- [x] The Wayland app ID matches the desktop-entry/icon identity; prepare the assets without switching the default launcher yet.
- [x] Plain launch exposes no inspector; explicit inspection supports view discovery, evaluation, screenshots, console and network access through the adapted repository helper.
- [x] Build/test/run commands, pins, runtime logs and known untested desktop behavior are documented.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.

2026-11-17: Implemented the standalone release shell, independent local.strix-halo.inference identity and cache profile, F11/window persistence, focus-only instance socket, native logs and opt-in WebKit inspector. Release rendering, six native window restarts, inspector operations and Wayland app-ID trace passed. The unstable Tauri feature is removed. Both real desktop binaries also ran simultaneously with fixture backends and independent scratch storage; inspector discovery showed the expected separate views, and both closed cleanly. See [desktop validation](../../../docs/desktop-validation.md) and [operations/debugging](../../../docs/desktop.md).
