# 02: Follow live container logs

**What to build:** Let the user inspect recent logs or follow new server output from either engine without changing inference lifecycle. Log following replaces the proposed foreground-start feature.

**Blocked by:** 01: Use engine-first launcher commands.

**Status:** resolved

- [x] The logs action retains its recent 100-line snapshot behavior by default and accepts an explicit follow option that shows recent output before following new lines.
- [x] Interrupting the viewer stops log following without stopping or restarting the inference container.
- [x] Missing containers produce useful feedback and a nonzero exit. Existing stopped containers can have their retained logs inspected, while auto-removed containers are reported as missing.
- [x] The viewer does not acquire or retain the engine startup lock. Container exit ends the viewer rather than leaving it waiting indefinitely.
- [x] Document snapshot and follow behavior and verify live following, interruption and continued generation on both engines. Do not add a foreground-start option.

## Comments

Completed with snapshot and follow modes. Offline policy checks and ShellCheck pass. Both live engines kept generating after viewer interruption. Following ended after container stop, and missing auto-removed container logs produced a clear error. No foreground-start behavior was added.
