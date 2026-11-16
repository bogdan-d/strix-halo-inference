# 05: Close the cross-app GPU exclusion gap

Status: resolved

Blocked by: [02](02-native-controls.md)

Spec: [Tauri desktop port](../spec.md)

## Scope

Inference currently rejects other inference-managed containers but does not reject Den’s ComfyUI container. Add the missing launcher-level check and actionable UI refusal without changing engine tuning or stopping an active workload.

Inspect simultaneous-start coordination: independent pre-start checks alone do not provide race-free exclusion. Establish the smallest compatible policy and test its boundary. The initial scope is this repository’s launcher and UI; if a shared lock requires a change to Den, record the exact companion change and coordinate it explicitly rather than silently modifying the sibling or claiming complete exclusion.

## Acceptance criteria

- [x] Starting any inference engine while strix-halo-den-comfyui is running is refused from both CLI and app.
- [x] Existing inference-engine exclusion remains intact, and refused starts leave the active engine and its workload untouched.
- [x] Tests cover the ComfyUI check and current inference start-lock behavior.
- [x] Simultaneous-start limitations or a coordinated cross-repository solution are explicitly documented and validated before claiming strict cross-app exclusion.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.

2026-11-17: Added the missing ComfyUI-name check inside inference’s existing start lock. Fixture starts of all three engines are refused while ComfyUI is present, without issuing a run command. Independent Den/inference locks still permit simultaneous-start races; the spec and desktop guide explicitly record the need for a coordinated Den-side lock change before claiming strict exclusion. See [desktop validation](../../../docs/desktop-validation.md) and [operations/debugging](../../../docs/desktop.md).
