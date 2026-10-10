# Local validation, October 10, 2026

Host: CachyOS, kernel `7.2.9-2-cachyos`, Ryzen AI Max+ 395, Radeon 8060S, approximately 125 GiB usable system RAM. Existing BIOS, IOMMU and kernel settings were preserved. Rootless Podman uses `runc`. GPU devices are directly accessible on this host, so supplementary-group preservation was not needed for these checks.

## Pinned artifacts

| Artifact | Selected version or revision |
|---|---|
| Halogen Flash image | 0.17.5, digest in `config/pins.env` |
| Gufo runtime image | 0.11.0, digest in `config/pins.env` |
| Gufo engine image label | `e3c0d4cc130721f2810999d8dbb9221cd092edf4` |
| Halogen native weights | `506567c641cfb737e0b01c1deff10813154c5529`, v2 checkpoint, lookup table and tokenizer |
| Gufo GGUF weights | `38bb39ee97821de2c9009abb7e93950eec396e66`, UD-Q4_K_XL shards and shared Q8 MTP head |

The Gufo pin is a published stable release, not the earlier PR candidate described in the historical research. Exact file sizes and SHA-256 hashes were obtained from pinned Hugging Face metadata. Non-LFS tokenizer hashes were computed from their pinned bytes. Both images were pulled by digest.

## Completed checks

- Shell syntax and ShellCheck pass. The offline model-integrity test rejects a size-correct corrupt existing shard without replacing it and rejects missing weights before launch.
- Gufo's `diagnose` passes inside the selected rootless container, detects `gfx1151` and reports ROCm 7.2.3. Its serve help confirms the configured model, context, speculative and cache flags.
- Halogen's container `rocminfo` detects the GPU. The rootless container hard memlock remains 8 MiB despite `--ulimit memlock=-1:-1`. Halogen's GPU-backed pinning still succeeds, while optional host `mlock` and NPU behavior remain untested and disabled.
- All eight selected Halogen files completed download and SHA-256 verification. The package totals 117,910,836,996 bytes, approximately 109.8 GiB.
- Halogen starts at one slot and 32K context with `/home/bogdan/models` mounted read-only and its own writable `/cache`. API and engine both report 0.17.5. The published port is localhost-only.
- Halogen produces `ready` for the non-thinking smoke prompt. The live test passes multi-turn secret-word recall, a named tool call with parsed JSON arguments, streaming disconnect slot release within 20 seconds, and generation after cancellation. The follow-up reports 24 cached prefix tokens, demonstrating in-process reuse.
- Halogen shuts down using the explicit stop command. No managed inference container remains running, and host available memory returns to approximately 119 GiB.

Halogen's startup log reports 62.1 GiB of weights, 0.9 GiB KV pool and 12.1 GiB working memory, 75.1 GiB total. Its separate 47.7 GiB lookup table is demand-paged. It warns that ordinary `MemAvailable` overstates memory reclaimable while the pinned weights are loaded. It also warns about fragmented host memory. Startup reached model readiness in approximately 11 seconds after download verification had warmed the file cache. This is not a cold-start benchmark, and the two-token smoke rate is not a meaningful throughput benchmark.

## Pending

Gufo's selected files total 114,121,223,040 bytes, approximately 106.3 GiB. Its full download and integrity verification remain in progress. Generation, autoregressive/MTP consistency, cache behavior, cancellation and shutdown are not yet validated with this model on this host. Gufo GPU diagnostics alone do not establish that its model will fit or serve correctly.

The resumed download runs in the transient user service `strix-halo-download-gufo.service`, with output appended to `/home/bogdan/.cache/strix-halo-inference/download-gufo.log`. This is a one-off download, not an enabled inference service. Inspect it with `systemctl --user status strix-halo-download-gufo` and stop it with `systemctl --user stop strix-halo-download-gufo`. Interrupted `.partial` files are preserved. Resume manually with `bin/models.sh download gufo`. A collected unit disappears after completion, so inspect the final log and run `bin/models.sh check gufo` to confirm completion.

Neither restart-safe disk restoration nor long-context performance has been tested. No host package, group, device-permission, login-limit, kernel or BIOS change was made. No persistent inference service, proxy, image-build CI or dashboard was added.
