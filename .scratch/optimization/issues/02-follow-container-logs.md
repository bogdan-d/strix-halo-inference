# 02: Follow live container logs

**What to build:** Let the user inspect recent logs or follow new server output from either engine without changing inference lifecycle. Log following replaces the proposed foreground-start feature.

**Blocked by:** 01: Use engine-first launcher commands.

**Status:** ready-for-agent

- [ ] The logs action retains its recent 100-line snapshot behavior by default and accepts an explicit follow option that shows recent output before following new lines.
- [ ] Interrupting the viewer stops log following without stopping or restarting the inference container.
- [ ] Missing containers produce useful feedback and a nonzero exit. Existing stopped containers can have their retained logs inspected, while auto-removed containers are reported as missing.
- [ ] The viewer does not acquire or retain the engine startup lock. Container exit ends the viewer rather than leaving it waiting indefinitely.
- [ ] Document snapshot and follow behavior and verify live following, interruption and continued generation on both engines. Do not add a foreground-start option.
