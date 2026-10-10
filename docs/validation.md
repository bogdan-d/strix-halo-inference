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
- All five selected Gufo files completed download. A separate verification pass after every download finished matched all 13 final files against their committed sizes and SHA-256 hashes. No corruption was detected.
- Gufo serves this model successfully at one session and 32K context, with speculation off and with the shared Q8 MTP head. Both modes pass conversation recall, forced tool arguments, streaming disconnect slot release and generation after cancellation. Follow-ups report 25 cached prefix tokens.
- Gufo's greedy autoregressive and MTP text is identical on two uncached prompts, one requesting a Fibonacci function and one explaining hash-mismatch handling. The MTP runs actually speculate, reporting 178 drafts with 159 accepted and 60 drafts with 29 accepted. This is a focused consistency check, not a general quality benchmark.
- Podman inspection confirms Gufo's central `/models` mount is read-only and its separate `/cache` mount is writable. Gufo shuts down cleanly and available host memory returns to approximately 120 GiB. About 1.3 GiB of previously swapped pages remains in swap afterward. No swap or cache flushing was performed.
- The startup lock stays in the launcher's shell rather than being inherited by the detached container monitor. A live check confirms the lock is released after launch and a second engine start is refused because the first engine is active. Both engines are stopped at the end of validation.

Halogen's startup log reports 62.1 GiB of weights, 0.9 GiB KV pool and 12.1 GiB working memory, 75.1 GiB total. Its separate 47.7 GiB lookup table is demand-paged. It warns that ordinary `MemAvailable` overstates memory reclaimable while the pinned weights are loaded. It also warns about fragmented host memory. Startup reached model readiness in approximately 11 seconds after download verification had warmed the file cache. This is not a cold-start benchmark, and the two-token smoke rate is not a meaningful throughput benchmark.

Gufo's MTP startup reports 84,599 MiB of GPU allocation, approximately 82.6 GiB, against the 108,000 MiB GPU memory limit. It reaches readiness in approximately 61 seconds in this run, including a 47-second full artifact fingerprint. These observations are not controlled cold-start or throughput benchmarks.

## Integrity record

Gufo's package totals 114,121,223,040 bytes, approximately 106.3 GiB. Together the packages total approximately 216.1 GiB. The complete post-download verification log is `/home/bogdan/.cache/strix-halo-inference/verify-models.log`, containing 13 `Verified` lines and successful completion records for both packages. Recheck at any time with `bin/models.sh verify halogen` and `bin/models.sh verify gufo`.

The download and verification used one-off transient user services, not enabled inference services. Their logs remain under `/home/bogdan/.cache/strix-halo-inference`. One resumed downloader logged a trailing shell parsing error after its final file was promoted because the script was edited while that process was running. The current script passes shell syntax checks, and the independent final-file verification completed successfully for every file afterward. The error did not indicate a failed or corrupted weight transfer.

## Remaining work

Neither restart-safe disk restoration nor long-context performance has been tested. No host package, group, device-permission, login-limit, kernel or BIOS change was made. No persistent inference service, proxy, image-build CI or dashboard was added.
