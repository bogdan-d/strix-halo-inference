# 04: Gufo with huihui's patch on the stock UD-Q4_K_XL

**What to build:** Make an abliterated Gufo model from the UD 3.1 `UD-Q4_K_XL` already on disk, using huihui's 3.56 GB patch, and test it on stock Gufo 0.34.0. The patch replaces three tensor families (`ssm_out`, `attn_output`, `ffn_down_shexp`) with huihui's v2 abliteration and leaves the routed experts alone. This is a different abliteration from orcarouter's, which r2 uses. Nobody has published results for a patched UD 3.1 file.

**Blocked by:** 01 (the patch is applied to the UD 3.1 file).

**Status:** ready-for-agent

Source: [huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/tree/main/patch-unsloth) at revision `cbc7fba13f1939ac3fa42b18d77ccf43847d74ef`, directory `patch-unsloth/`.

| File | Bytes | SHA-256 |
|---|---|---|
| `patch-unsloth-all/Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf` | 3,561,572,544 | `f3a42f213edb9117fd7f3873e0b29a9a94033cb49b91e100e792f6344adec752` |
| `patch-unsloth-all/Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf.key` | 64 | record after download |
| `patch-unsloth-Qwen3.8-Flash-Next-dec.py` | 9,659 | record after download |

The script is 269 lines of third-party Python. A skim on November 15 found only `gguf`, `numpy` and standard-library imports and an XOR step that decodes the patch with the key file; it copies a tensor unchanged, with a "Copied because dtype mismatch" line, when the patch has no entry of the same type. Read it in full before running it. In the UD-Q4_K_XL layout all three families are Q8_0 (36 `ssm_out`, 12 `attn_output`, 48 `ffn_down_shexp`), and the patch carries Q8_0 entries for all three, so 96 tensors should be patched.

- [ ] The three files are downloaded and pinned, and the script has been read in full.
- [ ] The script runs with no network access, the stock shards read-only and only a new output directory writable, with `--start-layer 0 --end-layer 48 --ablate-experts 2`.
- [ ] Its log shows 96 patched tensors and no dtype-mismatch copy in the three families.
- [ ] The output has the stock file's 1,224 tensor names, types and shapes and four loadable shards, and only the 96 patched tensors differ from stock by content.
- [ ] The inputs, exact command and output SHA-256 values are recorded.
- [ ] `bin/run.sh gufo` takes explicit model and MTP head overrides; the stock default is unchanged, the README documents them, and the offline tests pass.
- [ ] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `gufo`, using the stock shared MTP head, with the stock UD 3.1 model as the control for the refusal probe.
- [ ] Startup allocation is recorded (it should match stock), and results go in `docs/engine-updates.md` and `docs/abliterated-models.md`.

If the refusal probe fails with `--ablate-experts 2`, this route has no stronger setting; record that and move on. NeosQ (ticket 07) is then the Gufo candidate at this size.

## Comments
