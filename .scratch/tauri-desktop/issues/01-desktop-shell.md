# 01: Desktop shell and agent debugging

Status: ready-for-agent

Blocked by: None

Spec: [Tauri desktop port](../spec.md)

## Scope

Create a standalone single-WebView Tauri 2 app using the reusable Den runtime pieces. Give it a separate app ID, icon, single-instance socket, browser profile, window-state file, log and inspector record. Keep desktop data outside the per-engine caches. Port F11 and normal/maximized/fullscreen restore, rotated native logs and the explicit run --inspect workflow. Render bundled local dashboard assets; adapt Den’s build rather than copying its ComfyUI view machinery.

Build only in rootless Podman, using rechecked stable pins. Do not install host compilers or packages. No shared framework crate, remote ComfyUI view, library, job polling, download/media machinery or audio-sink preflight. Leave existing browser shortcuts active until ticket 06.

## Acceptance criteria

- [ ] The release app opens the bundled page in one WebView and coexists with Den without sharing identity or storage.
- [ ] A second launch focuses the existing app; F11 and normal/maximized/fullscreen restoration work across real restarts.
- [ ] The Wayland app ID matches the desktop-entry/icon identity; prepare the assets without switching the default launcher yet.
- [ ] Plain launch exposes no inspector; explicit inspection supports view discovery, evaluation, screenshots, console and network access through the adapted repository helper.
- [ ] Build/test/run commands, pins, runtime logs and known untested desktop behavior are documented.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.
