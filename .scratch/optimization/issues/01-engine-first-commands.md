# 01: Use engine-first launcher commands

**What to build:** Let the user keep the engine fixed while editing the action in shell history. All launcher actions use engine-first argument order, with matching help, printed instructions and documentation.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] All existing launcher actions work with engine-first argument order for Halogen and Gufo.
- [ ] Old action-first invocations fail without performing an action and explain how to migrate. Missing, invalid and extra arguments produce clear usage errors.
- [ ] Maintained callers, usage output, printed next steps and operational documentation use the new order consistently. Historical records remain clearly historical.
- [ ] Existing rootless operation, one-engine guard, startup locking, model mounts and runtime defaults remain unchanged.
- [ ] Focused checks exercise argument dispatch and rejected input. Verify readiness and a real generation request on each engine, one at a time, and record any checks not exercised.
