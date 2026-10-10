# Strix Halo inference

Run and compare Qwen3.8-Flash-Next with Halogen Flash and Gufo on a Ryzen AI Max+ 395, Radeon 8060S (`gfx1151`), and 128 GiB shared memory under CachyOS.

This repository currently contains research and the deployment plan. No engine has been installed or benchmarked on this host yet.

- [Engine research and sources](docs/qwen3.8-engine-research.md), checked October 10, 2026.
- [Podman setup patterns from the existing toolbox](docs/podman-reference.md).
- [Halogen upstream](https://github.com/peonist-ai/halogen-flash-server).
- [Gufo upstream](https://github.com/gufo-org/gufo).

## Deployment decisions

- Separate rootless Podman containers, using upstream images where practical.
- Pin image digests and model revisions after verifying compatible releases. Do not build around moving `latest` tags or unqualified review builds.
- Start with manual launches. Add user-level systemd Quadlets after both engines work reliably. Do not enable both at login.
- Run only one engine at a time. Separate containers do not create additional GPU memory, and both engines need most of the host's shared memory.
- Publish Halogen at `127.0.0.1:8731` and Gufo at `127.0.0.1:8080`, subject to checking for existing listeners. Do not expose internal engine ports.
- Pass `/dev/kfd` and `/dev/dri`, preserve the user's GPU groups, and grant only documented permissions. Avoid privileged containers and broad host mounts.
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
```

Download into those directories before launching inference. If using an engine's automatic downloader, temporarily mount only its destination subdirectory writable and point its model path there. Return to read-only mounts afterward. Record exact revisions, filenames and verification results in the repository, not the weight files themselves. Do not modify model files from another engine.

Keep generated prompt caches separately under `/home/bogdan/.cache/strix-halo-inference/halogen` and `/home/bogdan/.cache/strix-halo-inference/gufo`. Bind mount each engine's cache at its documented cache path. These caches contain conversation state and must not be committed or shared between engines.

On October 10, `/home/bogdan/models` contained empty model directories and four small `.ini` files, totaling approximately 32 KiB. No weight files were present. Existing contents are left untouched.

## Next steps

1. **Check container prerequisites.** Verify rootless Podman with `crun`, GPU device access, user groups, memory limits, free disk space and available ports. Review Halogen's proprietary engine license before pulling its image.
2. **Choose and download the weights.** Use Halogen's native v2 package for its recommended configuration. For Gufo, use the documented Unsloth UD-Q4_K_XL shards and matching shared Q8 MTP head. Leave vision out of the initial smoke test. Allow roughly 250 GiB of free space for both packages and download overhead, then refine against the selected file manifests.
3. **Bring up Halogen.** Add a minimal pinned launch configuration. Verify health, text generation, thinking controls, tool calls and multi-turn cache reuse. Start with one active request. Confirm how the chosen release sizes its context pool before reserving memory. Stop it and confirm memory is released.
4. **Bring up Gufo.** Repeat with a qualified release, one session and 32K context. Verify autoregressive output before enabling MTP. Check cancellation and multi-turn reuse, then stop it and confirm memory is released.
5. **Compare real workloads.** Use identical prompts, sampling, thinking settings and power profile. Measure cold prompt processing, follow-up latency, generation rate and memory at 8K and 32K, then 64K if comfortable. Record image digests, model revisions and output quality. Different native quantizations make this a practical setup comparison, not a pure engine benchmark.
6. **Keep the preferred configurations.** Add manual-start Quadlets with clear stop instructions. Increase context or concurrency only after checking desktop responsiveness and memory pressure. Add no proxy or dashboard until needed.

Large models can leave little memory for the desktop and other applications. Do not treat successful startup as proof that full context or multiple sessions will fit safely.
