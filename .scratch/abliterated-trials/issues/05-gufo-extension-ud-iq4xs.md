# 05: Gufo with the flash_next_iq extension and UD-IQ4_XS

**What to build:** Run UD 3.1 `UD-IQ4_XS` on stock Gufo 0.34.0 through the community `flash_next_iq` extension, first the stock file and then a copy abliterated with the huihui patch from ticket 04. The extension's README reports 80.8 GiB of device memory with two sessions, against the 89.12 GiB measured here for `UD-Q4_K_XL` with one. It serves `UD-IQ4_XS` only; `UD-IQ3_XXS` is out of reach until it accepts a Q6_K token embedding.

**Blocked by:** 01 (shared n-gram shard and the `UD-Q4_K_XL` baseline). The abliterated half is also blocked by 04 (patch on disk, script reviewed).

**Status:** ready-for-agent

Weights: [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF) at `d96201194f103c906994f283f504209dc8d2a10c`.

| File | Bytes | SHA-256 |
|---|---|---|
| `UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00004.gguf` | 10,946,618 | `93ff23a08e5cd7501f24fa16f5b415d5807d0175e04edd3ed6a7a41b601a4eef` |
| `UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00004.gguf` | 49,604,491,008 | `13d5dc8b93d039e4cfade5a9af7037f10c97f7ec4e53f75bd2e9ae34aae54aeb` |
| `UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00004.gguf` | 15,256,783,680 | `f6b9b5934908a2043732269dd740155d0f921d0763a1dcdd3452246311651f87` |
| `UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00004-of-00004.gguf` (same file as `UD-Q4_K_XL` shard 4: reflink it, do not download) | 28,800,138,432 | `5de8b5dbf89409acc39468decafd4a4a95b13c29d88a14b0356107897829ec36` |
| `MTP/mtp-Qwen3.8-Flash-Next-Q8_0.gguf` (standalone head) | 4,137,429,120 | `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1` |

Extension: [storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension) 0.2.0. Install the registry's reviewed revision with `gufo extension install flash_next_iq` if [gufo-extension#11](https://github.com/gufo-org/gufo-extension/pull/11) has merged. Otherwise the source is commit `9ce08cef17151aca3751ea2528765902054c54c4`, installed from a local checkout, and that is unreviewed native code: confirm with the user first. Installs from Git inside the stock image fail without the host's CA bundle mounted; a local directory avoids that. Keep the extension store in a per-engine directory outside Git, mounted into the container with `GUFO_EXTENSIONS_DIR`.

Known risk: the extension's README says the weight upload fails under Docker unless the container runs as root, and that rootless Podman with `--userns=keep-id`, which the launcher uses, is untested. If the upload fails here, stop and report rather than changing the container's user or security options.

- [ ] Shards 1 to 3 and the standalone MTP head are downloaded (69.0 GB), shard 4 is a reflink copy, and all five files verify.
- [ ] The extension is installed into the pinned Gufo image from the agreed source, with its revision recorded.
- [ ] `bin/run.sh gufo` can mount the extension store and take another MTP head through explicit settings (`GUFO_MODEL` already exists); the default start is unchanged and the README documents them.
- [ ] Stock `UD-IQ4_XS` passes trial checks 2 to 6 from the [spec](../spec.md#trial-checks) under the launcher's rootless Podman.
- [ ] Startup allocation with one session, `MemAvailable`, decode speed and a quality comparison against UD 3.1 `UD-Q4_K_XL` are recorded.
- [ ] Whether the extension accepts the shared MTP head already on disk is recorded (it would save about 1.3 GiB).
- [ ] The huihui patch is applied to `UD-IQ4_XS` as in ticket 04. In this layout `ssm_out` and `ffn_down_shexp` are Q8_0 and `attn_output` is Q6_K, all present in the patch, so 96 tensors should be patched with no dtype-mismatch copy. `gguf` 0.19.0 from PyPI, used in ticket 04, has no GGML `Q2_0` type, which two down-expert tensors of this file use, so the script needs a `gguf` build that knows it.
- [ ] The patched model passes trial checks 2 to 8, with stock `UD-IQ4_XS` as the control for the refusal probe.
- [ ] Results go in `docs/engine-updates.md`, `docs/gufo-extensions.md` and `docs/abliterated-models.md`.

## Comments
