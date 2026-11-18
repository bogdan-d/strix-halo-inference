# Gufo memory, smaller quants and extensions

Notes from November 14 and 15, 2026, with the November 17 move to Gufo 0.35.0. The `flash_next_iq` module is provisioned here for IQ4_XS and was rebuilt for 0.35.0 on November 17; the other extensions in the catalogue are not installed. The launcher pins stock Gufo 0.35.0 with Unsloth UD 3.1 `UD-Q4_K_XL` at revision `d96201194f103c906994f283f504209dc8d2a10c`; named weight profiles also select its Huihui v2 LoRA merge (see [weight profiles](weight-profiles.md)). Community numbers below are the publishers' claims, not local measurements, unless marked as measured here.

## IQ4_XS profiles on this host

The `iq4-xs` weight profile selects pinned UD 3.1 shards and the existing shared Q8_0 MTP head; `iq4-xs-lora` selects the Huihui v2 LoRA merge. Its n-gram shard is a reflink of the already verified Q4_K_XL shard. Download with `bin/models.sh download gufo iq4-xs`. Registry PR #11 was still open and unreviewed when rechecked on November 15. The user explicitly approved its pinned native source at `9ce08cef17151aca3751ea2528765902054c54c4` (version 0.2.0), and installation into the pinned Gufo image succeeded. Gufo reports `[installed, ready]`. Stock IQ4_XS passed rootless loading, short API/lifecycle checks and four sandboxed Pi coding runs at native 256K with one session. The original patched copy passed the same checks, answered all five probes stock refused, and preserved exact tool identifiers. Allocation is 72.64 GiB, about 16.49 GiB below Q4_K_XL’s 89.12 GiB. The full record is in [engine updates](engine-updates.md#november-15-gufo-iq4-xs-extension-trial).

The launcher mounts the extension store read-only only for profiles declaring `"extension": "flash_next_iq"`. The store is under `CACHE_ROOT/gufo-extensions/IMAGE_SHA256/SOURCE_REVISION`, separate from prompt caches, so cache clearing cannot remove the module and an engine image update requires a fresh installation: after every Gufo image update, rerun the install command below with the new `GUFO_IMAGE` (done for 0.35.0 on November 17). `python bin/weights.py gufo extension iq4-xs` prints its host path. Missing installations disable the profile in the dashboard and fail before container creation. Gufo additionally checks its own module build identity when loading.

Build the inspected, approved local source using the pinned `GUFO_IMAGE`, rootless `--userns=keep-id:uid=1000,gid=1000`, `--network none`, a read-only container filesystem and source mount, temporary `/tmp`, and only the extension store writable on the host. Run `gufo extension install /src --yes`, then `gufo extension list` using the same store; retain the build log and confirm `flash_next_iq 0.2.0` is ready. No custom engine image or host installation is required. Inference keeps the launcher's existing GPU permissions and localhost endpoint. If weight upload fails under rootless Podman, stop and report; do not switch to root or relax security settings.

The installation used this command with `SOURCE` pointing to the extracted pinned checkout outside Git:

```bash
source config/pins.env
STORE="$(python bin/weights.py gufo extension iq4-xs)"
mkdir -p -- "$STORE"
podman run --rm --network none --read-only --tmpfs /tmp:rw \
  --userns=keep-id:uid=1000,gid=1000 \
  --env HOME=/tmp --env XDG_CACHE_HOME=/tmp/cache \
  --volume "$SOURCE:/src:ro" --volume "$STORE:/extensions:rw" \
  --env GUFO_EXTENSIONS_DIR=/extensions "$GUFO_IMAGE" \
  gufo extension install /src --yes
podman run --rm --network none --read-only --tmpfs /tmp:rw \
  --userns=keep-id:uid=1000,gid=1000 \
  --volume "$STORE:/extensions:ro" --env GUFO_EXTENSIONS_DIR=/extensions \
  "$GUFO_IMAGE" gufo extension list
```

Once provisioned, use `bin/run.sh gufo start --weights iq4-xs --wait`. The ordinary `default` and `lora` Q4_K_XL profiles do not load this module. The shared head passed the same API/lifecycle checks and real speculative generation. Its 32 draft-block tensors are byte-identical to the standalone head’s; both allocate 72.64 GiB in this extension, so the smaller file did not save GPU memory. The standalone file remains on disk as a trial reference. Long-context quality, near-capacity requests and image inputs remain untested.

## Gufo memory at the current pin

Measured here on November 14 with Gufo 0.34.0, each configuration started alone, given a smoke generation and stopped. The allocation is the engine's startup report; free memory is MemAvailable while it ran.

| Context | MTP | GPU allocation | Saved | MemAvailable |
|---|---|---|---|---|
| 262144 (launcher default) | on | 89.12 GiB | — | about 24 GiB |
| 131072 | on | 85.77 GiB | 3.4 GiB | 25.7 GiB |
| 262144 | off | 85.99 GiB | 3.1 GiB | 25.5 GiB |
| 131072 | off | 82.89 GiB | 6.2 GiB | 28.5 GiB |
| 32768 | off | 80.57 GiB | 8.6 GiB | 30.7 GiB |

The weights alone are 76.9 GiB, so the floor is near 80 GiB. Halogen 0.20.4 reserves 78.7 GiB at full context with its drafter on. While Gufo ran at the default, the kernel pushed about 4 GiB of idle desktop memory to the disk swapfile (swappiness 100); that is harmless but makes switching back to idle apps slower.

## Smaller Flash-Next quants

Stock Gufo 0.34.0, and 0.35.0 with a byte-identical loader, loads Flash-Next experts only as Q4_K, Q5_K, Q6_K, Q5_1 or Q8_0, and the per-layer n-gram table only as IQ4_NL, Q8_0 or BF16 ([`weights.cpp`](https://github.com/gufo-org/gufo/blob/v0.34.0/src/models/qwen38_flash_next/weights.cpp)). `UD-Q4_K_XL` with its bundled IQ4_NL table is therefore the smallest file it accepts. The maintainers declined sub-4-bit support in core ([#1220](https://github.com/gufo-org/gufo/issues/1220), not planned) and point to community extensions; [#454](https://github.com/gufo-org/gufo/issues/454) remains open.

Tensor formats read from the GGUF headers with HTTP range requests, at Unsloth revision `f5d175de2cf7` (UD 3.1). Sizes are GiB.

| Quant | Total | Without the n-gram table | Expert formats | Stock Gufo |
|---|---|---|---|---|
| `UD-Q4_K_XL` | 103.68 | 76.86 | Q4_K 41.31, Q5_1 25.20, Q8_0 4.15, Q5_K 1.07 | Loads |
| `UD-IQ4_XS` | 87.24 | 60.42 | Q5_0 17.72, IQ3_XXS 16.75, IQ4_XS 14.11, IQ4_NL 5.71, IQ2_S 1.50 | Rejected |
| `UD-Q3_K_XL` | 82.87 | 56.05 | IQ3_XXS 22.73, IQ4_NL 11.43, Q5_0 10.74, IQ4_XS 4.98, IQ2_S 2.00 | Rejected |

Every quant bundles the same 26.82 GiB IQ4_NL n-gram table. IQ4_XS sizes above are corrected to the verified local shard sizes, including its two Q2_0 tensors and metadata.

A second scan on November 15 at the same revision also found GGML `Q2_0` on two down-expert layers of `UD-IQ4_XS`, which the format column omits, and read `UD-IQ3_XXS` (83.6 GB): gate/up experts IQ2_S on 26 layers, IQ3_XXS on 21 and IQ4_XS on 1; down experts IQ4_NL on 45 layers and `Q2_0` on 3. Outside the experts it differs from `UD-IQ4_XS` in two places: `token_embd` and all 36 `ssm_out` tensors are Q6_K, where `UD-IQ4_XS` has IQ4_XS and Q8_0. The `UD-IQ4_XS` shards are byte-identical at `084c631a` (the extension's pin, below), `d9620119` and `f5d175de`.

### Unsloth Dynamic 3.1

Unsloth replaced the GGUFs with Dynamic 3.1 builds on November 4, claiming about 10 to 15% higher accuracy and up to 50% fewer tokens than other quants of the same size. All four `UD-Q4_K_XL` shards changed (about 104 GiB to download); the shared Q8_0 MTP head did not. Gufo's docs and CI now use revision `d96201194f103c906994f283f504209dc8d2a10c` and state that tensor types and shapes are unchanged, so moving to it changes quality, not memory. The n-gram table now sits in its own shard and can be swapped for Q8_0 or BF16 (Gufo does not read Q5_1); Gufo has no `--ple` option, so a swap follows Unsloth's [engram guide](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/blob/main/engram/README.md) with `set_split.py`.

### Community options

[storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension), MIT, is the route that keeps stock Gufo. Version 0.2.0 loads into Gufo 0.34.0 and, rebuilt, into 0.35.0 (extension API 0.3.20) and serves Unsloth's `UD-IQ4_XS` only, as the UD 3.1 file and the October export, with MTP, `--mmproj` and continuation checkpoints. Its expert kernels cover every UD 3.1 expert format, including GGML `Q2_0`, but its device upload rejects a Q6_K token embedding ([`device_model.cpp`](https://github.com/storm1er/flash-next-iq-gufo-extension/blob/9ce08cef17151aca3751ea2528765902054c54c4/src/kernels/rocm/device_model.cpp), inspected on November 15; IQ4_XS subsequently run here), so it cannot serve UD 3.1 `UD-IQ3_XXS`, which stores `token_embd` as Q6_K. Its README reports 80.8 GiB of device memory for UD 3.1 `UD-IQ4_XS` with two sessions, and 46 to 60 tok/s decoding at 174K depth with MTP. It uses Unsloth's standalone Q8_0 MTP head (4.1 GB) rather than the `shared` head on disk; the local trial also validated the shared head and uses it in the profiles above. In the 0.34.0 container, installing from a Git or registry source fails with an SSL error because the image's Git has no CA bundle; the README's fix is to mount the host's bundle and set `GIT_SSL_CAINFO` and `SSL_CERT_FILE`, and a local copy or the publisher's CI image avoids the problem. The README also says the weight upload fails under Docker unless the container runs as root, and that rootless Podman with `--userns=keep-id`, which the launcher here uses, was untested by the publisher. Local loading and generation now pass with those rootless settings, without relaxing permissions. Registry review is pending in [gufo-extension#11](https://github.com/gufo-org/gufo-extension/pull/11); once merged, `gufo extension install flash_next_iq` installs a reviewed revision.

[johandevlabs/gufo-iq4_xs](https://github.com/johandevlabs/gufo-iq4_xs), MIT, is a fork of Gufo 0.33.0 with the same goal, published as `ghcr.io/johandevlabs/gufo-toolboxes/gufo-runtime:edge`. It lacks the 0.34.0 fixes and uses a moving tag. Its README reports, at 262144 context with MTP and images:

| Quant | Unsloth revision | Download | Same next token as `UD-Q4_K_XL` | Mean KL | GPU weights | GPU memory in use |
|---|---|---|---|---|---|---|
| UD 3.1 `UD-IQ4_XS` | `d9620119` | 93.7 GB | 89.4% | 0.096 | 60.1 GiB | 74.1 GiB |
| UD 3.1 `UD-IQ3_XXS` | `d9620119` | 83.6 GB | 88.3% | 0.123 | 50.6 GiB | 64.8 GiB |
| October `UD-IQ4_XS` | `38bb39ee` | 93.7 GB | 88.8% | 0.119 | 59.8 GiB | — |
| October `UD-IQ3_XXS` | `38bb39ee` | 82.0 GB | 85.5% | 0.186 | 50.2 GiB | — |

It reports 33 to 34 tok/s decoding without MTP and 42 to 50 tok/s with MTP on mixed text, on a 96 GB GMKtec Evo-X2. Compared with Gufo's 89.12 GiB here, UD 3.1 `UD-IQ3_XXS` would leave about 24 GiB more free, and about 14 GiB more than Halogen, at the cost of roughly one next token in nine differing from `UD-Q4_K_XL`. Only the fork runs `UD-IQ3_XXS`. With the extension the choice is `UD-IQ4_XS`. The local one-session comparison is 72.64 GiB against Q4_K_XL’s 89.12 GiB, a 16.49 GiB saving; the earlier 80.8 GiB publisher figure used two sessions and was not directly comparable.

### Trial status

The extension route is provisioned; the smaller-quant fork remains a separate future trial:

1. **Stock Gufo with the extension, `UD-IQ4_XS`: provisioned, 16.49 GiB saved with one session.** Use the named profiles above. Rootless upload, shared MTP, API tools/cancellation and the stock model’s matched Pi coding checks pass. See the update record for the completed trial results and limits.
2. **The fork, `UD-IQ3_XXS`, about 24 GiB saved.** This needs johandevlabs' image, which is Gufo 0.33.0 behind a moving tag: pin it by digest and treat it as a separate engine build. Recheck the extension before choosing it; if a later version accepts a Q6_K token embedding, `UD-IQ3_XXS` moves to route 1.

For an abliterated model on route 1, see [abliterated builds](abliterated-models.md#what-each-engine-reads).

## Extensions

Gufo extensions add models or quantizations as native code built into Gufo. An extension builds only against a host in the same extension API minor series: Gufo 0.34.0 and 0.35.0 are series 0.3 (0.35.0 reports API 0.3.20), so extensions declaring `>= 0.2.x` or older need Gufo 0.33.0 or earlier ([versioning](https://github.com/gufo-org/gufo/blob/v0.34.0/docs/extension-api.md#versions)). The [reviewed registry](https://github.com/gufo-org/gufo-extension) lists extensions whose exact source revisions a maintainer reviewed for malicious or careless code; it does not vouch for quality or speed, and an installed extension runs native code with the user's permissions. Other sources install with a warning.

Found on GitHub on November 15, 2026. API versions are from each repository's `extension.json` on its default branch.

### Built against API 0.3, usable with Gufo 0.34.0 and 0.35.0

| Extension | Adds | API | Registry |
|---|---|---|---|
| [storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension) | Flash-Next Unsloth `UD-IQ4_XS` | `>= 0.3.0` | Pending, #11 |
| [gufo-org/lfm3-gufo-extension](https://github.com/gufo-org/lfm3-gufo-extension) | LFM3 1.7B text, LFM3-VL 2B, LFM3-Audio 2B, d1-Omni 2B | `>= 0.3.4` at 0.6.0 | Yes, but the reviewed 0.4.0 targets API 0.2 |
| [gufo-extensions/nemotron](https://github.com/gufo-extensions/nemotron) | Nemotron family | `>= 0.3.0` | No |
| [gufo-extensions/nemotron_asr](https://github.com/gufo-extensions/nemotron_asr) | Nemotron 3.5 streaming speech to text | `>= 0.3.0` | No |
| [gufo-extensions/voxcpm](https://github.com/gufo-extensions/voxcpm) | VoxCPM2 text to speech | `>= 0.3.0` | No |
| [gufo-extensions/omnivoice](https://github.com/gufo-extensions/omnivoice) | OmniVoice speech | `>= 0.3.0` | No |
| [D3rPapst/upscale-gufo-extension](https://github.com/D3rPapst/upscale-gufo-extension) | Real-ESRGAN 2× and 4× image upscaling | `>= 0.3.0` | Pending, #12 |
| [loom-fun/loom-gufo-extension](https://github.com/loom-fun/loom-gufo-extension) | Loom model packages as Gufo text models, prototype | `>= 0.3.15`, not checked against 0.34.0 | No |

### Built against API 0.2 or older, needing Gufo 0.33.0 or earlier

| Extension | Adds | API | Registry |
|---|---|---|---|
| [franzmoca/ds41-gufo-extension](https://github.com/franzmoca/ds41-gufo-extension) | DeepSeek V4.1 Flash with DSpark drafting, vision, tool calls and SSD expert streaming | `>= 0.2.17` | Yes, `deepseek41flash` 0.2.0 |
| [slimsami/strycast-qwen35moe-gufo-extension](https://github.com/slimsami/strycast-qwen35moe-gufo-extension) | Qwen3.6-35B-A3B and Ornith 1.5 122B with MTP and DFlash2 | `>= 0.2.21` | Yes, `strycast_qwen35moe`; 0.1.0 pending, #13 |
| [brunobarbosaux-ai/flint-gufo-extension](https://github.com/brunobarbosaux-ai/flint-gufo-extension) | Flint 40B MoE | `>= 0.2.7` | Yes, `flint` 0.2.0 |
| [franzmoca/gemma4-gufo-extension](https://github.com/franzmoca/gemma4-gufo-extension) | Gemma 4 31B, 31B QAT and 26B-A4B, work in progress | `>= 0.2.14` | No |
| [D3rPapst/moss-image-gufo-extension](https://github.com/D3rPapst/moss-image-gufo-extension) | MOSS-Image text to image | `>= 0.1.15` | No |
| [rikaaa0928/fish-drama3-gufo-extension](https://github.com/rikaaa0928/fish-drama3-gufo-extension) | Undescribed | `>= 0.1.0` | No |
| [codibre/qwen38-flash-next-gsq-gufo-extension](https://github.com/codibre/qwen38-flash-next-gsq-gufo-extension) | Flash-Next GSQ-RCO pruned 256-expert variants down to IQ1_M, about 43.9 GB | `>= 0.1.16` | No |
| [codibre/deepseek41-gufo-extension](https://github.com/codibre/deepseek41-gufo-extension) | DeepSeek V4.1, an earlier take than franzmoca's | `>= 0.1.16` | No |

The codibre GSQ variant is the smallest Flash-Next found, but it is a pruned model rather than the same weights. Recheck API versions and registry entries before a trial; both lists were moving daily.
