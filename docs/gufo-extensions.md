# Gufo memory, smaller quants and extensions

Notes from November 14 and 15, 2026, for later trials. Nothing here is provisioned or configured; the launcher still runs stock Gufo 0.34.0 with Unsloth `UD-Q4_K_XL` at revision `38bb39ee97821de2c9009abb7e93950eec396e66`. Community numbers below are the publishers' claims, not local measurements, unless marked as measured here.

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

Stock Gufo 0.34.0 loads Flash-Next experts only as Q4_K, Q5_K, Q6_K, Q5_1 or Q8_0, and the per-layer n-gram table only as IQ4_NL, Q8_0 or BF16 ([`weights.cpp`](https://github.com/gufo-org/gufo/blob/v0.34.0/src/models/qwen38_flash_next/weights.cpp)). `UD-Q4_K_XL` with its bundled IQ4_NL table is therefore the smallest file it accepts. The maintainers declined sub-4-bit support in core ([#1220](https://github.com/gufo-org/gufo/issues/1220), not planned) and point to community extensions; [#454](https://github.com/gufo-org/gufo/issues/454) remains open.

Tensor formats read from the GGUF headers with HTTP range requests, at Unsloth revision `f5d175de2cf7` (UD 3.1). Sizes are GiB.

| Quant | Total | Without the n-gram table | Expert formats | Stock Gufo |
|---|---|---|---|---|
| `UD-Q4_K_XL` | 103.68 | 76.86 | Q4_K 41.31, Q5_1 25.20, Q8_0 4.15, Q5_K 1.07 | Loads |
| `UD-IQ4_XS` | 86.79 | 59.97 | Q5_0 17.72, IQ3_XXS 16.75, IQ4_XS 14.11, IQ4_NL 5.71, IQ2_S 1.50 | Rejected |
| `UD-Q3_K_XL` | 82.87 | 56.05 | IQ3_XXS 22.73, IQ4_NL 11.43, Q5_0 10.74, IQ4_XS 4.98, IQ2_S 2.00 | Rejected |

Every quant bundles the same 26.82 GiB IQ4_NL n-gram table.

### Unsloth Dynamic 3.1

Unsloth replaced the GGUFs with Dynamic 3.1 builds on November 4, claiming about 10 to 15% higher accuracy and up to 50% fewer tokens than other quants of the same size. All four `UD-Q4_K_XL` shards changed (about 104 GiB to download); the shared Q8_0 MTP head did not. Gufo's docs and CI now use revision `d96201194f103c906994f283f504209dc8d2a10c` and state that tensor types and shapes are unchanged, so moving to it changes quality, not memory. The n-gram table now sits in its own shard and can be swapped for Q8_0 or BF16 (Gufo does not read Q5_1); Gufo has no `--ple` option, so a swap follows Unsloth's [engram guide](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/blob/main/engram/README.md) with `set_split.py`.

### Community options

[storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension), MIT, is the preferred route. It loads into stock Gufo 0.34.0 (extension API 0.3) and serves the Unsloth IQ family, UD 3.1 and the October export, with MTP, `--mmproj` and continuation checkpoints. It covers every UD 3.1 expert format, including GGML `Q2_0`. Its README reports 80.8 GiB of device memory for UD 3.1 `UD-IQ4_XS` with two sessions, and 46 to 60 tok/s decoding at 174K depth with MTP. In the 0.34.0 container, installing from a Git or registry source fails with an SSL error, so it needs a local copy or the publisher's CI image with the extension compiled in. Registry review is pending in [gufo-extension#11](https://github.com/gufo-org/gufo-extension/pull/11); once merged, `gufo extension install flash_next_iq` installs a reviewed revision.

[johandevlabs/gufo-iq4_xs](https://github.com/johandevlabs/gufo-iq4_xs), MIT, is a fork of Gufo 0.33.0 with the same goal, published as `ghcr.io/johandevlabs/gufo-toolboxes/gufo-runtime:edge`. It lacks the 0.34.0 fixes and uses a moving tag. Its README reports, at 262144 context with MTP and images:

| Quant | Unsloth revision | Download | Same next token as `UD-Q4_K_XL` | Mean KL | GPU weights | GPU memory in use |
|---|---|---|---|---|---|---|
| UD 3.1 `UD-IQ4_XS` | `d9620119` | 93.7 GB | 89.4% | 0.096 | 60.1 GiB | 74.1 GiB |
| UD 3.1 `UD-IQ3_XXS` | `d9620119` | 83.6 GB | 88.3% | 0.123 | 50.6 GiB | 64.8 GiB |
| October `UD-IQ4_XS` | `38bb39ee` | 93.7 GB | 88.8% | 0.119 | 59.8 GiB | — |
| October `UD-IQ3_XXS` | `38bb39ee` | 82.0 GB | 85.5% | 0.186 | 50.2 GiB | — |

It reports 33 to 34 tok/s decoding without MTP and 42 to 50 tok/s with MTP on mixed text, on a 96 GB GMKtec Evo-X2. Compared with Gufo's 89.12 GiB here, UD 3.1 `UD-IQ3_XXS` would leave about 24 GiB more free, and about 14 GiB more than Halogen, at the cost of roughly one next token in nine differing from `UD-Q4_K_XL`.

### Trial plan

When a fast connection is available: download UD 3.1 `UD-IQ3_XXS` at Gufo's revision into a new manifest beside the existing `UD-Q4_K_XL` files, install `flash_next_iq` into stock Gufo 0.34.0 (from the registry if #11 has merged), then run the usual checks and record the startup allocation, `tests/live.py` and a quality comparison against `UD-Q4_K_XL`. The `UD-IQ3_XXS` header scan has not been run; the extension's format list covers its expected formats.

## Extensions

Gufo extensions add models or quantizations as native code built into Gufo. An extension builds only against a host in the same extension API minor series: Gufo 0.34.0 is series 0.3, so extensions declaring `>= 0.2.x` or older need Gufo 0.33.0 or earlier ([versioning](https://github.com/gufo-org/gufo/blob/v0.34.0/docs/extension-api.md#versions)). The [reviewed registry](https://github.com/gufo-org/gufo-extension) lists extensions whose exact source revisions a maintainer reviewed for malicious or careless code; it does not vouch for quality or speed, and an installed extension runs native code with the user's permissions. Other sources install with a warning.

Found on GitHub on November 15, 2026. API versions are from each repository's `extension.json` on its default branch.

### Built against API 0.3, usable with Gufo 0.34.0

| Extension | Adds | API | Registry |
|---|---|---|---|
| [storm1er/flash-next-iq-gufo-extension](https://github.com/storm1er/flash-next-iq-gufo-extension) | Flash-Next Unsloth IQ quants | `>= 0.3.0` | Pending, #11 |
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
