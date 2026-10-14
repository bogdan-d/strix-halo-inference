# 04: Choose the helpers and their clients

**What to build:** Decide which NPU helpers to keep loaded and what will call them, using the measurements from 03. The candidates are agent-memory or project search on an embedder, a decider for routing or triage in a Pi extension, and the streaming guard. Record the decision as an ADR and remove unused model files.

**Blocked by:** 03

**Status:** needs-triage

- [ ] Each kept helper has a named client and a reason that outweighs its memory and Flash-speed cost.
- [ ] The decision is recorded under `docs/adr/`.
- [ ] `config/npu-files.tsv` lists only kept models, and unused files are removed with the user's approval.
