# 05: Compare thinking effort for routine coding

**What to build:** Help the user choose between medium and xhigh thinking for routine coding using a small, repeatable Pi comparison on both engines, rather than changing defaults based on intuition.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Use a small set of representative coding tasks with unchanged executable checks and fresh equivalent starting workspaces for each run.
- [ ] Compare medium and xhigh on Halogen and Gufo, running one engine at a time. Keep sampling, model revisions, context capacity, MTP and task inputs fixed within each engine comparison. Control or explicitly record cache conditions.
- [ ] Record total task time, passing checks, tool calls and failures or output truncation. Use repeated paired runs or clearly label results as exploratory when repetition is insufficient.
- [ ] Document how to select thinking effort in Pi and a recommendation bounded by the observed results. Do not claim a universal quality or speed improvement from a small sample.
- [ ] Preserve live Pi defaults and unrelated settings. Keep private prompts, generated conversation state and temporary workspaces out of the public repository, while retaining only concise non-private findings and repeatable task instructions.
