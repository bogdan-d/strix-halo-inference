# NPU models stay opt-in until a client needs one

Halogen can serve small models on the NPU beside the Flash model, and both tested sets work on this host (see [First NPU run](../engine-updates.md#first-npu-run)). No client calls any of them yet: agent-memory searches with SQLite full-text ranking by design and holds a handful of entries, no Pi extension asks a decider, and the streaming guard only labels replies, which has little use for single-user local coding.

We therefore load no NPU model by default. `NPU_MODELS` stays an explicit launcher setting, and a model is chosen when a concrete client needs it, with its memory and Flash-speed cost weighed then. All downloaded NPU files stay on disk and in `config/npu-files.tsv`, so any set can be tried without downloading again.

## Consequences

- An unset `NPU_MODELS` keeps Halogen as before: no NPU memory, no Flash slowdown and no held fabric clock, which costs about 2.3 W.
- Loading models without a client would cost about 6.2 GiB of host RAM for the small set, or 8.9 GiB for the 4B pair, for no use.
- The files take 17.3 GB of disk. After a Halogen pin change they must still be rechecked with `bin/npu-manifest.sh` and `bin/models.sh download npu`, even while unused.
- Reopen this when a client is planned, for example a Pi extension that routes prompts with `decider-0.8b` or semantic recall on an embedder.
