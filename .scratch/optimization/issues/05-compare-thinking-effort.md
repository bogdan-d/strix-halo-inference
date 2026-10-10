# 05: Compare thinking effort for routine coding

**What to build:** Help the user choose between medium and xhigh thinking for routine coding using a small, repeatable Pi comparison on both engines, rather than changing defaults based on intuition.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Use a small set of representative coding tasks with unchanged executable checks and fresh equivalent starting workspaces for each run.
- [x] Compare medium and xhigh on Halogen and Gufo, running one engine at a time. Keep sampling, model revisions, context capacity, MTP and task inputs fixed within each engine comparison. Control or explicitly record cache conditions.
- [x] Record total task time, passing checks, tool calls and failures or output truncation. Use repeated paired runs or clearly label results as exploratory when repetition is insufficient.
- [x] Document how to select thinking effort in Pi and a recommendation bounded by the observed results. Do not claim a universal quality or speed improvement from a small sample.
- [x] Preserve live Pi defaults and unrelated settings. Keep private prompts, generated conversation state and temporary workspaces out of the public repository, while retaining only concise non-private findings and repeatable task instructions.

## Comments

Completed 16 measured trials on two public synthetic tasks with two reversed-order repeats per engine and effort. All passed fixed independent checks. Medium was faster in all eight pairs, with approximately 59% lower mean task time on Halogen and 44% lower on Gufo. Recommendation is limited to small, well-specified edits, with xhigh retained for substantial work. The repeatable harness and concise findings are documented in the routine-coding comparison. Live defaults were unchanged, temporary state was removed, and both engines were stopped afterward.
