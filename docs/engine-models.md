# Models each engine supports

All three engines serve Qwen3.8 Flash-Next. Gufo also serves Qwen3.8 27B through the `27b-heretic` profile. This page lists the other models each engine can serve at the pinned release, from upstream documentation checked November 9, 2026, and rechecked for the release changes of November 17, and marks which ones this repo provisions. Upstream support is a publisher claim; only models marked as provisioned have files listed in the model manifests under `config/`, and only those the [update record](engine-updates.md) names have been run here.

Abliterated Flash-Next builds for each engine, with picks and compatibility notes, are collected in [abliterated builds](abliterated-models.md).

## Halogen 0.20.7

Halogen runs one model on the GPU, Flash-Next, and small models on the NPU beside it, on the same port. The launcher passes NPU models with `NPU_MODELS`; see the [README](../README.md#npu-models).

### Flash-Next variants on the GPU

| Variant | Status here |
|---|---|
| Native v2 `.hgn` checkpoint, 62.1 GiB, plus the FP8 n-gram table, 47.7 GiB | Provisioned and used |
| Draft head `qwen38-flash-next-drafter-r2.hgn`, 1.42 GiB, new in 0.20.6 | Fallback overlay if the HT4 file is absent |
| Draft head `qwen38-flash-next-drafter-r2-ht4.hgn`, 4-bit projections | Pinned and provisioned beside all three checkpoints. Halogen 0.20.7 selects this 1.39 GiB overlay automatically with MTP on |
| Vision tower `qwen38-flash-next-vision.hgn` | Optional download, provisioned here. Enable with `VISION=on` |
| GGUF of the same model, read directly: unsloth `UD-IQ4_XS` and `UD-Q4_K_XL`, bartowski `IQ4_XS`, mradermacher `i1-IQ4_XS`, `Q4_K_M`/`Q4_K_S`, ggml-org `IQ4_NL` | Not configured; the launcher selects only the `.hgn` package. Gufo's `UD-Q4_K_XL` shards are already on disk. [GGUF guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.7/docs/gguf.md) |

A separate preview image, `0.18.14-flint-preview`, serves RecursiveSI's Flint, a 40B mixture-of-experts model, instead of Flash-Next. It is not pinned or used here. [Flint preview](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.7/README.md#flint-preview).

### NPU models

Each named model is fetched from its own `peonist-ai/halogen-npu-*` repository. `HALOGEN_DOWNLOAD` stays unset here, so only models whose files are in `config/npu-files.tsv` can start. [NPU guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.7/docs/NPU.md).

| Model | Base model | Use, route | Provisioned |
|---|---|---|---|
| `decider-0.8b` | Qwen3.5-0.8B classifier | Probabilities over 2 to 10 options | Yes |
| `decider-4b` | Qwen3.5-4B classifier | Same, better on harder questions | Yes |
| `d3-lite` | Decision 3.0, 0.8B (vLLM Semantic Router) | Decisions over text and pictures, up to 255 options | Yes |
| `d3-nano` | Decision 3.0, 2B | Same | No, removed October 24 |
| `qwen3-embedding-0.6b` | Qwen3-Embedding-0.6B | `/v1/embeddings` | Yes |
| `qwen3-embedding-4b` | Qwen3-Embedding-4B | `/v1/embeddings` | No |
| `embeddinggemma-2` | EmbeddingGemma 2 | Text, picture and sound embeddings in one space | Yes |
| `wemm-embedding-4b` | WEMM embedding, 4B | Embeddings, pictures included | Yes |
| `qwen3-reranker-0.6b` | Qwen3-Reranker-0.6B | `/v1/rerank` | No |
| `qwen3-reranker-4b` | Qwen3-Reranker-4B | `/v1/rerank`, shares the 4B embedder's files | No |
| `qwen3guard-gen-0.6b` | Qwen3Guard-Gen-0.6B | `/v1/moderations` | No |
| `qwen3guard-stream-0.6b` | Qwen3Guard-Stream-0.6B | Labels a Flash reply while it streams | Yes |
| `halogen-spotter-0.6b`, new in 0.19.0 | Halogen Spotter | Reads tool results for the opt-in agent guard (`HALOGEN_AGENT_GUARD`), a preview | No |
| `qwen3.5-2b` | Qwen3.5-2B, thinking off | Short text generation beside Flash | No |
| `flux2-klein-4b` | FLUX.2-klein-4B | `/v1/images/generations` and `/v1/images/edits`, 256 to 1024 pixels | No |
| `qwen3-asr-0.6b`, `qwen3-asr-1.7b` | Qwen3-ASR | `/v1/audio/transcriptions`, up to 20 minutes | No |
| `qwen3-tts-0.6b-customvoice`, `qwen3-tts-1.7b-customvoice` | Qwen3-TTS CustomVoice | `/v1/audio/speech`, nine preset voices | Yes |

### Checkpoints you supply on the NPU

These load from a path under `/models`, converted at first start. On our read-only models volume the conversion runs at every start. None is provisioned.

| Checkpoint | Use |
|---|---|
| Fine-tunes of Qwen3.5-0.8B, Qwen3-Embedding-0.6B, Qwen3-Reranker-0.6B or Qwen3Guard-Gen-0.6B, and Qwen3-0.6B sequence classifiers | Decisions, embeddings, reranking, moderation, `/classify` |
| LiquidAI LFM3-1.7B or a fine-tune | Chat completions; 0.20.6 adds a `:qad` format for Liquid's `LFM3-1.7B-QAD-Q4_0.gguf`, about 48 tokens a second after a 1,024-token prompt |
| LiquidAI d1-2B | Decisions over text, pictures and video, on `/v1/systemone` |
| LiquidAI LFM3-VL-2B or a fine-tune, new in 0.18.23 | Chat with pictures and video |
| LiquidAI LFM3-Audio-2B or a fine-tune, new in 0.18.23 | Speech in, speech out, `/v1/audio/transcriptions` and `/v1/audio/speech` |
| LiquidAI LFM3-Omni-2B, new in 0.18.23 | Pictures, video with sound, speech in, and text or speech out, on one model id |
| `ATH-MaaS/OvisOCR3`, Apache 2.0, new in 0.20.0 | Document pages to Markdown, with tables as HTML and formulas as LaTeX, served as `OvisOCR3` on the chat routes; one or two pictures a request, about 20 seconds a typical page. The image ships only its NPU programs, and the launcher's `NPU_MODELS` takes model ids, not the `/models/OvisOCR3` path it needs. [Guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.7/docs/NPU.md#your-own-ovisocr3) |

## Gufo 0.35.0

Gufo identified single images and their order on this host on November 24, 2026. See [projector support by profile](weight-profiles.md#gufo-image-input). Gufo serves one model per process. `gufo serve llm|embedding|image|asr|tts|video|decision` picks the kind, and the launcher here starts `serve llm` with Flash-Next or Qwen3.8 27B. [Model index](https://github.com/gufo-org/gufo/blob/v0.35.0/docs/models/README.md). Smaller Flash-Next quants, measured memory by context and MTP, and community extensions are collected in [Gufo memory, smaller quants and extensions](gufo-extensions.md).

| Model | Weights | Use | Provisioned |
|---|---|---|---|
| Qwen3.8 Flash-Next | unsloth `UD-Q4_K_XL` GGUF, four shards; optional shared Q8_0 MTP head and BF16 vision projector | Text and images | Images validated with and without MTP on stock and LoRA Q4_K_XL and both IQ4_XS extension profiles |
| Qwen3.8 27B | unsloth `UD-Q4_K_XL` (16.45 GiB) or `UD-Q8_K_XL` (29.30 GiB) GGUF; optional z-lab DFlash2 draft | Dense text and images | `27b-heretic` serves text with UD-Q4_K_XL, the Heretic adapter and DFlash2 at 128K. Optional BF16 projector for images |
| DeepSeek V4 Flash | antirez `deepseek-v4-gguf`, mixed IQ2/Q2/Q8, 80.76 GiB | Text, with optional DSpark speculation | No |
| EmbeddingGemma 2 | `google/embeddinggemma-2`, BF16 | Text, image, video and audio embeddings on `/v1/embeddings`; `--npu` embeds text on the NPU, new in 0.35.0 | No |
| Qwen-Image-2.1 and 2.1 Turbo | BF16 safetensors, about 33 GB | Image generation and editing, with true CFG, image to image and an A1111 (`sdapi`) route since 0.35.0; non-commercial Qwen Research License | No |
| Qwen3-ASR 1.7B | BF16 safetensors | Speech to text; 0.6B unsupported. `--npu`, new in 0.35.0, runs it on the NPU with the GPU off at about half the GPU's speed, about 1.3 s for 10 s of audio | No |
| Qwen3-TTS 12Hz 1.7B, CustomVoice, VoiceDesign or Base | BF16 safetensors | Speech from preset voices, a voice description or reference audio; 0.6B unsupported. `--npu`, new in 0.35.0, runs every variant on the NPU and CPU with the GPU off at about 1.4x real time | No |
| MiniMax H3 FL2VA | `MiniMaxAI/MiniMax-H3` safetensors | Text to video with sound, as MP4 | No |

Gufo's NPU modes load XRT on first use from `/dev/accel/accel0`, which the launcher already passes to every engine; only `serve llm` is wired up here. Upstream recommends keeping the NPU out of runtime suspend and warns that heavy GPU and NPU work at once can hang some Strix Halo hosts ([amd/xdna-driver#1605](https://github.com/amd/xdna-driver/issues/1605)). [Install notes](https://github.com/gufo-org/gufo/blob/v0.35.0/docs/install.md).

## Strixite 0.7.1

Strixite runs only Qwen3.8-Flash-Next, from its own `wemoh/Qwen3.8-Flash-Next-strixw` weights: the converted model, its n-gram table and an optional vision tower with preprocessor configuration, all provisioned here. Upstream plans no other models or platforms. [README](https://github.com/shawnshekari/strixite/blob/v0.7.1/README.md).
