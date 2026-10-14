# 03: First NPU validation and Flash slowdown

**What to build:** Start Halogen with each downloaded NPU model and record the real cost. Use one representative request per route: a decision with logprobs, a text embedding and an image embedding, and a streamed chat with `"guard": true`.

**Blocked by:** 02

**Status:** resolved

- [x] Each model loads, Halogen's file check passes, and its route answers.
- [x] Startup memory with each model set is recorded against the 30.6 GiB left without NPU models.
- [x] Flash decode and prefill are measured with the NPU idle and while it runs a sustained embedding or decision load.
- [x] Stop releases NPU and host memory, and Halogen restarts cleanly.
- [x] Anything not exercised is listed in `docs/engine-updates.md`.

## Comments

- October 14: the first start with `decider-0.8b,embeddinggemma-2,qwen3guard-stream-0.6b` passed Halogen's XRT, fabric clock and file checks, then exited: the container could lock 8 MiB and the set needs 5,436,197 KiB. Desktop processes inherit `user@1000.service`'s `LimitMEMLOCK=8M`, so the user added a drop-in at `/etc/systemd/system/user@1000.service.d/memlock.conf`, set to 32G. The launcher now refuses NPU models below 4 GiB, because `--rm` discards the container's own error. After logging back in, check `ulimit -Hl` (33554432), then retry. README's container-boundaries note that memlock "remains 8 MiB" needs updating once verified.
- October 14, after the reboot: both sets loaded and every route answered. Small set about +6.2 GiB host RAM, 4B pair about +8.9 GiB. Under continuous NPU load Flash decode fell 5 to 7% (small) and 11 to 12% (4B), prefill 2 to 7%. Results in `docs/engine-updates.md` (First NPU run). Startup memory is compared as host RAM used, because Halogen's own figure does not include the NPU.
