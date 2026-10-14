# Reply-end reuse benchmark

`bench.py OUTPUT.json [EFFORT]` replays a Pi-shaped tool-using conversation against a running Halogen at temperature 0 and writes per-request prompt, cached, output and time-to-first-token figures. Start Halogen with an empty `CACHE_ROOT` for each configuration so earlier runs cannot help. Results from October 14, 2026 are summarized in [the update record](../../docs/engine-updates.md#reply-end-reuse).
