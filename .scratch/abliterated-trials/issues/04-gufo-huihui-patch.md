# 04: Gufo with huihui's patch on the stock UD-Q4_K_XL

**What to build:** Make an abliterated Gufo model from the stock `UD-Q4_K_XL` already on disk, using huihui's 3.56 GB patch, and test it on stock Gufo 0.34.0. The patch replaces three tensor families (`ssm_out`, `attn_output`, `ffn_down_shexp`) with huihui's v2 abliteration and leaves the routed experts alone. This is a different abliteration from orcarouter's, which r2 uses. Nobody has published results for a patched UD 3.1 file.

**Blocked by:** None. Done on November 15 on the October file, at the user's request, ahead of ticket 01.

**Status:** resolved

Source: [huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/tree/main/patch-unsloth) at revision `cbc7fba13f1939ac3fa42b18d77ccf43847d74ef`, directory `patch-unsloth/`.

| File | Bytes | SHA-256 |
|---|---|---|
| `patch-unsloth-all/Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf` | 3,561,572,544 | `f3a42f213edb9117fd7f3873e0b29a9a94033cb49b91e100e792f6344adec752` |
| `patch-unsloth-all/Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf.key` | 64 | `2ed56e36f9a9c4f806d9fb48f5ef9e06ed5d1ab3b4f6b8ee31e19ef5b8ea9667` |
| `patch-unsloth-Qwen3.8-Flash-Next-dec.py` | 9,659 | `69d15f62facd3f9d16bdeaf13cab9077e3568b5f274a843d28fd1796eb31d22a` |

The script is 269 lines of third-party Python. Read in full on November 15, it uses only `gguf`, `numpy` and standard-library imports and an XOR step that decodes the patch with the key file; it copies a tensor unchanged, with a "Copied because dtype mismatch" line, when the patch has no entry of the same type. In the UD-Q4_K_XL layout all three families are Q8_0 (36 `ssm_out`, 12 `attn_output`, 48 `ffn_down_shexp`), and the patch carries Q8_0 entries for all three, so 96 tensors should be patched.

- [x] The three files are downloaded and pinned, and the script has been read in full.
- [x] The script runs with no network access, the stock shards read-only and only a new output directory writable, with `--start-layer 0 --end-layer 48 --ablate-experts 2`.
- [x] Its log shows 96 patched tensors and no dtype-mismatch copy in the three families.
- [x] The output has the stock file's 1,224 tensor names, types and shapes and four loadable shards, and only the 96 patched tensors differ from stock by content.
- [x] The inputs, exact command and output SHA-256 values are recorded.
- [x] `bin/run.sh gufo` takes an explicit model override (`GUFO_MODEL`); the stock default is unchanged, the README documents it, and `python tests/run.py` passes.
- [x] Trial checks 2 to 8 from the [spec](../spec.md#trial-checks) pass with `gufo`, using the stock shared MTP head, with the stock model as the control for the refusal probe.
- [x] Startup allocation is recorded (it should match stock), and results go in `docs/engine-updates.md` and `docs/abliterated-models.md`.

If the refusal probe fails with `--ablate-experts 2`, this route has no stronger setting; record that and move on. NeosQ (ticket 07) is then the Gufo candidate at this size.

## Comments

- November 15: done against the pinned October `UD-Q4_K_XL` (`38bb39ee`), not UD 3.1, because the user asked for it before ticket 01. All boxes pass; details are in `docs/engine-updates.md` (November 15 trial). The script is safe as read: no network, subprocess, `eval`, `exec` or delete calls, writes only to the output directory. 96 tensors patched, nothing else changed, 5 of 5 stock refusals answered, `tests/live.py` passed, 5 of 5 exact identifiers, 89.12 GiB as stock.
- The patch files are pinned in the update record, not in a manifest: trial manifest support is still ticket 02's. Only a Gufo model override (`GUFO_MODEL`) was added; an MTP head override was not needed and is left to ticket 05.
- To repeat: a virtual environment with `gguf==0.19.0` and `tqdm==4.70.1` (hash-pinned, `--no-deps`, system NumPy), the script run under `bwrap --unshare-all` with the inputs read-only, then `verify_patch.py STOCK_DIR PATCHED_DIR` and `probe.py gufo` from this directory. The patch run takes under a minute.
- Ticket 01 re-applies the patch to the UD 3.1 file once it is on disk.
