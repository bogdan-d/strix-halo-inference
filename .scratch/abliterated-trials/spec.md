# UD 3.1 weights and abliterated model trials

## Goal

Move Gufo to Unsloth's UD 3.1 `UD-Q4_K_XL`, then try an abliterated Flash-Next on each engine, cheapest and best-evidenced first. Drafted November 15, 2026. Ticket 03 is complete with HT43 preferred for abliterated Halogen use on this host; ticket 02 is complete on Halogen 0.20.4 with its native verifier table-order limitation documented; ticket 04 completed on the October weights; ticket 01 is complete on UD 3.1, with the user requesting named weight profiles and deletion of both superseded October copies after validation.

Background and sources are in [abliterated builds](../../docs/abliterated-models.md) and [Gufo memory, smaller quants and extensions](../../docs/gufo-extensions.md). Pins, sizes and hashes below were read from the Hugging Face API on November 15; recheck them before downloading.

## Order

| Ticket | Step | Download | At 13 MB/s |
|---|---|---|---|
| [01](issues/01-gufo-ud31-q4kxl.md) | Update Gufo to UD 3.1 `UD-Q4_K_XL` | 111.3 GB | 2.4 h |
| [02](issues/02-halogen-r2.md) | Halogen: Quat3rnion r2 | 88.7 GB | 1.9 h |
| [03](issues/03-halogen-ht43-abliterated.md) | Halogen: HT43 abliterated | 57.6 GB | 1.2 h |
| [04](issues/04-gufo-huihui-patch.md) | Gufo: huihui patch on the stock file (done November 15, on the October file) | 3.6 GB | 5 min |
| [05](issues/05-gufo-extension-ud-iq4xs.md) | Gufo: `flash_next_iq` extension with `UD-IQ4_XS` | 69.0 GB | 1.5 h |
| [06](issues/06-strixite-ngkzngkz.md) | Strixite: ngkzngkz weights, local n-gram table first | 71.6 GB (plus 51.8 GB if the table is rejected) | 1.5 h (plus 1.1 h) |
| [07](issues/07-remaining-candidates.md) | Maybe: the remaining candidates | per candidate | |

Tickets 01 to 06 total about 402 GB, roughly 8.6 hours at the 13 MB/s measured through the VPN on November 15. Four parallel streams gave the same total, so the link was the limit.

## Disk

`/home/bogdan/models` is btrfs with 2.5 TB free. Beyond the downloads, the patch in tickets 04 and 05 writes full copies of what it patches (about 111 GB and 94 GB), so budget about 610 GB of new space, or 660 GB if ticket 06 needs the second n-gram table. The user approved deleting both October copies during ticket 01; they were removed after the UD 3.1 replacements passed validation. Where a trial needs a file that is already on disk under another name, use `cp --reflink=always`, which costs no space on btrfs, then verify the copy's SHA-256.

## Constraints

- One engine at a time. Before each start, check that no managed engine is running (another agent thread may be using one), and after each stop verify memory was released.
- Trials do not change defaults. Only ticket 01 changes what `bin/run.sh gufo start` serves. Every other trial selects its files through an explicit launcher setting and leaves the stock model as the default.
- Every downloaded file is pinned by repository revision, size and SHA-256 in committed configuration, and verified before use. Locally generated files (patched GGUFs) are recorded by input pins, exact command and output SHA-256.
- Weights stay under `/home/bogdan/models`, mounted read-only for inference. Endpoints stay on localhost.
- Third-party code (the huihui patch script, the Gufo extension) is read before it runs, and runs without network access and without write access to anything but its output directory. Ask before relaxing container security for either.
- Do not delete or overwrite existing model files without the user's approval. Move them aside instead.

## Trial checks

Each trial runs these and records the results in [engine-updates.md](../../docs/engine-updates.md), with anything not exercised listed as such:

1. Size and SHA-256 of every file (`bin/models.sh verify` once the manifest covers it).
2. `bin/run.sh ENGINE start --wait`, then `bin/run.sh ENGINE status` and `bin/run.sh ENGINE smoke`, at native context with speculative decoding on.
3. `python tests/live.py ENGINE` for Halogen and Gufo, or `python tests/strixite_live.py` for Strixite: conversation, tools and cancellation.
4. The startup allocation the engine reports and `MemAvailable` while it runs, against the stock model's figures.
5. Decode speed on the same prompt as the stock model.
6. `bin/run.sh ENGINE stop`, then confirm memory was released.

Abliterated trials add the two checks below, both run by [probe.py](probe.py); [verify_patch.py](verify_patch.py) compares a patched GGUF with its source.

7. A refusal probe: at least three prompts that the stock model on the same engine refuses, run on stock first as the control, then on the trial. Record the category and whether each was answered. Keep prompt texts and outputs out of the repository.
8. A tool call that must copy an exact case-sensitive identifier, as in [gufo-org/gufo#780](https://github.com/gufo-org/gufo/issues/780), since no abliterated build's author reports testing this beyond one forced call.

## Launcher and manifest changes

The original plan below described missing launcher support. Ticket 01 now adds shared `config/weights.json` profiles, `bin/run.sh ENGINE start --weights PROFILE`, per-profile caches, alternative manifests with pinned source paths, and dashboard selection for all engines. Follow `docs/weight-profiles.md`; later tickets register their files there instead of adding competing override mechanisms. Extension loading remains ticket 05 work. Original requirements:

- **Trial manifests** (ticket 02): let `bin/models.sh download|verify|check` handle a manifest whose lines name their own repository and revision, as the NPU manifest already does, so trial files are pinned in `config/` like everything else.
- **Halogen** (ticket 02): an explicit checkpoint override. Halogen finds the n-gram table beside the checkpoint, and the launcher takes the tokenizer and vision paths from the same directory, so a trial directory holds the trial checkpoint plus reflink copies of the stock companions.
- **Gufo** (tickets 04 and 05): `GUFO_MODEL`, added with ticket 04, selects a trial GGUF. Ticket 05 adds an MTP head override and a mount for the extension store.
- **Strixite** (ticket 06): an explicit model directory override.

Update the README's launcher documentation with each setting, and keep `tests/run.py` passing.

## What can be done before the VPN is off

None of these needs bandwidth: the launcher and manifest changes above with their offline tests, reading the huihui patch script and the extension source (both small), the stock-model control runs for the refusal probe, and the `ppl` reference dump of the stock Halogen checkpoint (ticket 02). The last two need the GPU free.

## Open decisions

- **October `UD-Q4_K_XL` shards:** delete after ticket 01 passes, or keep (111 GB)? User decision during ticket 01: delete both October stock and patched copies after the UD 3.1 replacements pass validation.
- **Extension source:** if [gufo-extension#11](https://github.com/gufo-org/gufo-extension/pull/11) has not merged, ticket 05 installs unreviewed native code from a pinned commit. Confirm before installing.
- **After the trials:** the user requested regular named weight profiles during ticket 01; Gufo now offers validated UD 3.1 `default` and `abliterated`. Halogen now also offers validated `abliterated-r2` and `abliterated-ht43`; the Strixite trial still requires its own provisioning and validation.

## Halogen reference for ticket 03

Ticket 02 saved the full WikiText-2 corpus, stock reference, source pins and result JSON outside Git at `$HOME/.cache/strix-halo-inference/trials/halogen-r2`. Reuse that exact corpus and reference with the same pinned Halogen 0.20.4 image, chunk 1024, sequence 262144 and native tool attention settings for the HT43 comparison. See [the r2 update record](../../docs/engine-updates.md#november-15-halogen-r2-abliterated-trial) for hashes and the verifier limitation; recheck each new file independently.

Ticket 03 reused those artifacts and added `r2-wikitext2.ref`, `ht43-vs-stock.json` and `ht43-vs-r2.json` beside them. Both HT43 passes produced the same perplexity. The [HT43 record](../../docs/engine-updates.md#november-15-ht43-abliterated-trial) contains the comparison and recommendation.
