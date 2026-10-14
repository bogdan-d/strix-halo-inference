# 03: First NPU validation and Flash slowdown

**What to build:** Start Halogen with each downloaded NPU model and record the real cost. Use one representative request per route: a decision with logprobs, a text embedding and an image embedding, and a streamed chat with `"guard": true`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Each model loads, Halogen's file check passes, and its route answers.
- [ ] Startup memory with each model set is recorded against the 30.6 GiB left without NPU models.
- [ ] Flash decode and prefill are measured with the NPU idle and while it runs a sustained embedding or decision load.
- [ ] Stop releases NPU and host memory, and Halogen restarts cleanly.
- [ ] Anything not exercised is listed in `docs/engine-updates.md`.
