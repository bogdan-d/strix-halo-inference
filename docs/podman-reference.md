# Podman setup reference

Before implementing containers here, use the user's existing toolbox as a reference for practical build and launch patterns. This is not a dependency on that repository and does not authorize changing it.

Inspected `/var/mnt/xdata/code/strix-halo/amd-strix-halo-toolboxes` at local commit `feb2174c94cb17afa860bc8133526258220d2ed9` on October 10, 2026. Its origin is [bogdan-d/amd-strix-halo-toolboxes](https://github.com/bogdan-d/amd-strix-halo-toolboxes), with [kyuz0 upstream](https://github.com/kyuz0/amd-strix-halo-toolboxes). The local branch was one commit ahead of origin. Consult the local checkout for the inspected state, which may not yet be published. No scripts were executed or reference files changed.

## Patterns to borrow

| Pattern | Local reference files | Adaptation here |
|---|---|---|
| Project-relative helpers and Bash argument arrays | `bin/build.sh`, `bin/run.sh` | Keep launch entry points simple, with explicit engine selection and quoted argument arrays. Resolve paths independently of the caller's working directory. |
| Environment overrides take precedence over local defaults | `bin/env-defaults.sh` | If local configuration becomes necessary, preserve override precedence. Its parser reads assignments without evaluating shell code. Avoid adding a parser before it is needed. |
| Version pins invalidate the correct build layers | `bin/build.sh`, `docs/build.md` | Pin upstream image digests first. For a custom Gufo build, pass an exact source commit as a build argument and record the actual revision. Keep reproducibility pins versioned rather than only in a private `.env`. |
| Dependency caches survive application rebuilds | `containers/Containerfile`, `containers/Containerfile.rocmfpx` | If custom builds are required, cache dependencies separately from source and compilation. Keep unrelated engine caches independent. Halogen's binary distribution does not require recreating the llama.cpp build matrix. |
| Trimmed runtime stages and OCI provenance | `containers/Containerfile`, `docs/build.md` | Keep compilers out of custom runtime images where practical. Record source and revision labels in images we build. Record the digest of upstream images we consume. |
| GPU devices and supplementary groups | `bin/run.sh`, `docs/podman.md` | For HIP engines, validate `/dev/dri`, `/dev/kfd` and `--group-add keep-groups` with rootless Podman and `crun`. Verify image-specific user mapping rather than assuming the same container user works everywhere. |
| Log selected image and exact launch arguments | `bin/run.sh` | Make failures diagnosable, preserve exit codes and redact secrets. Avoid logging credential values. |
| Bounded load test with cleanup | `bin/run.sh` | Check the engine's health endpoint, capture useful failure logs and stop the test container. A llama.cpp `model loaded` log match is not a generic readiness contract. |
| Full logs with concise build progress | `bin/build.sh` | Add only if local builds become noisy. Retain the full log and original builder failure status. |

The toolbox uses Buildah by default and supports `BUILDER=podman`. Its cached, multi-stage Containerfiles are useful references, but this project should first use the engines' own supported images. Building a full stock/fork/backend matrix would add work unrelated to trying these two engines.

## Boundaries to change rather than copy

- **Model mounts:** the existing wrapper mounts its model directory writable. Here, bind mount `/home/bogdan/models:/models:ro` for inference and keep downloads a separate writable step. Preserve existing files and avoid `:U`, which can recursively change ownership of shared models.
- **Networking:** the existing wrapper publishes ports without restricting the host address. Here, publish only on `127.0.0.1` and give each engine its own host port. An in-container listener on `0.0.0.0` does not require publishing on every host interface.
- **Permissions:** the wrapper uses `seccomp=unconfined`, `label=disable` and host IPC. These are not universal GPU requirements. Use each engine's documented IPC and locked-memory needs, then justify additional permissions from an actual failure. Do not copy blanket security relaxation or privileged mode.
- **Environment:** the wrapper forwards most variable names found in `.env`. Here, forward only required engine settings. Keep credentials separate from public pins and model manifests.
- **Lifecycle:** the wrapper uses `--replace` for named containers. Here, prefer an explicit stop before switching engines. Avoid replacing an active model process as a side effect of starting another service.
- **Engine policy:** llama.cpp flash-attention, mmap, batch, layer-offload, GGML and ROCmFPX settings are not Halogen or Gufo settings. Derive runtime flags from the pinned engine release. In particular, preserve each engine's own embedding-table paging strategy.
- **Host policy:** the reference `AGENTS.md` recommends IOMMU and memory changes for its earlier setup. Keep this host's current settings for our first baseline. Do not turn historical recommendations into automatic setup steps.
- **Host configuration:** preset generators can optionally update coding-tool configurations. Keep that out of inference startup here. Configure a client separately after its endpoint works.

## First implementation

Add the smallest manual launch path for each engine, with explicit model paths, pinned images, independent cache mounts, localhost publishing and documented stop commands. Validate one engine at a time. Use Halogen's native package and Gufo's documented GGUF/MTP pair before experimenting with cross-engine weight reuse.

Once manual launches pass health, generation, cancellation and memory-release checks, translate the working settings into user-level systemd Quadlets if convenient. Defer image-build CI, backend matrices, model discovery, client-config generators and proxy routing until there is a demonstrated need.
