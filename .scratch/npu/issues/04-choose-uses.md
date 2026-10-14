# 04: Choose the helpers and their clients

**What to build:** Decide which NPU helpers to keep loaded and what will call them, using the measurements from 03. The candidates are agent-memory or project search on an embedder, a decider for routing or triage in a Pi extension, and the streaming guard. Record the decision as an ADR and remove unused model files.

**Blocked by:** 03

**Status:** resolved

- [x] Each kept helper has a named client and a reason that outweighs its memory and Flash-speed cost.
- [x] The decision is recorded under `docs/adr/`.
- [x] `config/npu-files.tsv` lists only kept models, and unused files are removed with the user's approval.

## Comments

- October 14: the user chose to load no NPU model by default and build no client yet, and to keep all downloaded files. No helper is kept loaded, so none needs a client. Recorded in [ADR 0001](../../../docs/adr/0001-npu-models-stay-opt-in.md).
