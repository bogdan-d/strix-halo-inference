# 11: Add a Qwen3.8 27B profile to the Gufo launcher

Status: resolved

Originally deferred, then requested on November 22. Ticket [09](09-gufo-27b-lora.md) made Gufo's 27B provider merge an adapter at load ([gufo-org/gufo#1323](https://github.com/gufo-org/gufo/pull/1323)), and this ticket brings the Heretic profile to the dashboard and launcher.

## Original implementation notes

Checked against this repository at `df76b36`.

- **Fork image:** `GUFO_FORK_REVISION` has to move to a commit with the 27B work, `89dd58f3` on branch `feat/qwen27-lora` of bogdan-d/gufo, then `bin/gufo-fork.sh` and a new `GUFO_FORK_IMAGE` digest. That image also serves the existing `lora` profile, so `lora` needs its usual checks again. A stock 27B profile without an adapter can use the pinned upstream image.
- **Launcher:** for Gufo, `bin/run.sh` hardcodes `--served-model-name qwen3.8-flash-next` and `--speculative mtp --mtp-model`. 27B needs its own served name and `--speculative dflash2 --dflash-model`. `bin/weights.py` accepts the profile keys `model`, `manifest`, `directory`, `mtp`, `adapter` and `extension`; the drafter needs a key or a rule there.
- **Profile and manifest:** an entry in `config/weights.json` and a manifest with pinned sources for the target, the drafter and the adapter. The files are already in `/home/bogdan/models`; their revisions, sizes and hashes are in `/var/mnt/xdata/code/strix-halo/gufo-build/qwen27/models.tsv`. `mmproj-BF16.gguf` (0.87 GiB, images) was not downloaded.
- Serve 27B as `qwen3.8-27b` in Gufo. Register it in Pi as `gufo/qwen3.8-27b` and print `pi --provider gufo --model qwen3.8-27b --thinking xhigh` after startup. Flash-Next uses `qwen3.8-flash-next`. Both dashboards list configured weight profiles, and Gufo status reads the running container's profile label and model path.
- Start the 27B profile at 128K context (131072 tokens) and advertise that window in Pi. Bogdan reports 27B prefill is roughly 3–4 times slower than Flash-Next.
- **Tests:** the offline launcher tests with additions for the new fields, then for each new profile `bin/models.sh verify`, `start --wait`, `smoke`, `tests/live.py` and `stop` with the memory-release check. No new kinds of test.

## Which profile

UD-Q4_K_XL with the adapter is the one the user wanted: 25,167 MiB of device memory and 10.5 tokens/s without speculation at 32768 context, against 35,409 MiB and 7.2 tokens/s for UD-Q8_K_XL with the adapter. A stock UD-Q4_K_XL profile is a small extra if a baseline is wanted.

## Comments

November 22: Implemented `27b-heretic` with the Heretic adapter, DFlash2 and a 128K limit. Both local Pi installations register `gufo/qwen3.8-27b`. The optional stock baseline was outside this implementation. Both the new profile and the existing Flash-Next `lora` passed the launcher and GPU lifecycle checks, including stop with memory release. [Validation record](../../../docs/engine-updates.md#november-22-qwen38-27b-on-gufo).
