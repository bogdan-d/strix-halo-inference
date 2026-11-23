# 01: Gufo's qwen27b_target_test fails with "invalid argument" on this host

Status: needs-triage

Found on November 23 during the 27B LoRA side-path work (ticket [10](../../abliterated-trials/issues/10-gufo-27b-q4-adapter-routes.md)). The fork's real-weight GPU test `qwen27b_target_test` ends with `invalid argument` on UD-Q4_K_XL, for stock weights as well as with an adapter, so the LoRA work did not cause it.

## Known

- Logs: `/var/mnt/xdata/code/strix-halo/gufo-build/logs/sp-target-stock.log` and `sp-target-lora.log`. Neither contains a backtrace.
- The implementer attributed it to a HIP error in `QwenGpuArena::SaveSnapshot` at small contexts, the 2D KV-cache copy near `src/models/qwen/hip/arena.cpp:584` (fork at `0d2e2359`). An independent reviewer confirmed the stock failure but could not confirm the location without a backtrace.
- The side-path checks avoided it by comparing without snapshots.

## Next

1. Reproduce on the pinned upstream code (no fork commits) at the test's default context, and capture the failing HIP call with `AMD_LOG_LEVEL` or a debugger.
2. If upstream reproduces, report it to gufo-org/gufo with the failing call, context size and model; otherwise find which fork commit introduces it.
