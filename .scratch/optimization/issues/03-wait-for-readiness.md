# 03: Wait for engine readiness during startup

**What to build:** Offer optional startup waiting so success means the selected engine is ready to accept requests, not merely that its container was created.

**Blocked by:** 01: Use engine-first launcher commands.

**Status:** resolved

- [x] Startup remains detached by default and offers an explicit wait option that checks the selected engine's readiness rather than liveness alone.
- [x] Waiting has a documented finite timeout and bounded individual probes. Container exit is detected and reported promptly with a nonzero result.
- [x] Timeout reports that the engine is not ready, leaves the container available for inspection and explains how to inspect logs or stop it. Interrupting the wait does not silently stop inference.
- [x] Successful waiting prints the local endpoint and a matching Pi launch command. The startup lock is released once container creation completes, not held throughout readiness polling.
- [x] Focused checks cover readiness success, container exit and timeout. Verify successful waited startup and a real generation request on both engines, one at a time, and document the behavior.

## Comments

Completed with optional readiness waiting, bounded probes and a configurable 300-second default timeout. Offline checks cover success, timeout, early exit, invalid timeout and startup-lock release before probing. Both engines completed waited startup and real generation at 256K with MTP enabled. Timeout does not stop containers.
