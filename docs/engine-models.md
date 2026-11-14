# Models each engine supports

All three engines are configured here for Qwen3.8-Flash-Next only. This page lists the other models each engine can serve at the pinned release, from upstream documentation checked November 9, 2026, and marks which ones this repo provisions. Upstream support is a publisher claim; only models marked as provisioned have files listed in `config/*-files.tsv`, and only those the [update record](engine-updates.md) names have been run here.

Abliterated Flash-Next builds for each engine, with picks and compatibility notes, are collected in [abliterated builds](abliterated-models.md).

## Halogen 0.20.4

Halogen runs one model on the GPU, Flash-Next, and small models on the NPU beside it, on the same port. The launcher passes NPU models with `NPU_MODELS`; see the [README](../README.md#npu-models).

### Flash-Next variants on the GPU

| Variant | Status here |
|---|---|
| Native v2 `.hgn` checkpoint, 62.1 GiB, plus the FP8 n-gram table, 47.7 GiB | Provisioned and used |
| Vision tower `qwen38-flash-next-vision.hgn` | Provisioned, opt-in with `VISION=on` |
| GGUF of the same model, read directly: unsloth `UD-IQ4_XS` and `UD-Q4_K_XL`, bartowski `IQ4_XS`, mradermacher `i1-IQ4_XS`, `Q4_K_M`/`Q4_K_S`, ggml-org `IQ4_NL` | Not configured; the launcher selects only the `.hgn` package. Gufo's `UD-Q4_K_XL` shards are already on disk. [GGUF guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/gguf.md) |

A separate preview image, `0.18.14-flint-preview`, serves RecursiveSI's Flint, a 40B mixture-of-experts model, instead of Flash-Next. It is not pinned or used here. [Flint preview](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/README.md#flint-preview).

### NPU models

Each named model is fetched from its own `peonist-ai/halogen-npu-*` repository. `HALOGEN_DOWNLOAD` stays unset here, so only models whose files are in `config/npu-files.tsv` can start. [NPU guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/NPU.md).

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
| LiquidAI LFM3-1.7B or a fine-tune | Chat completions |
| LiquidAI d1-2B | Decisions over text, pictures and video, on `/v1/systemone` |
| LiquidAI LFM3-VL-2B or a fine-tune, new in 0.18.23 | Chat with pictures and video |
| LiquidAI LFM3-Audio-2B or a fine-tune, new in 0.18.23 | Speech in, speech out, `/v1/audio/transcriptions` and `/v1/audio/speech` |
| LiquidAI LFM3-Omni-2B, new in 0.18.23 | Pictures, video with sound, speech in, and text or speech out, on one model id |
| `ATH-MaaS/OvisOCR3`, Apache 2.0, new in 0.20.0 | Document pages to Markdown, with tables as HTML and formulas as LaTeX, served as `OvisOCR3` on the chat routes; one or two pictures a request, about 20 seconds a typical page. The image ships only its NPU programs, and the launcher's `NPU_MODELS` takes model ids, not the `/models/OvisOCR3` path it needs. [Guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/docs/NPU.md#your-own-ovisocr3) |

## Gufo 0.34.0

Gufo serves one model per process. `gufo serve llm|embedding|image|asr|tts` picks the kind, and the launcher here starts only `serve llm` with Flash-Next. [Model index](https://github.com/gufo-org/gufo/blob/v0.34.0/docs/models/README.md). Smaller Flash-Next quants, measured memory by context and MTP, and community extensions are collected in [Gufo memory, smaller quants and extensions](gufo-extensions.md).

| Model | Weights | Use | Provisioned |
|---|---|---|---|
| Qwen3.8 Flash-Next | unsloth `UD-Q4_K_XL` GGUF, four shards; optional shared Q8_0 MTP head and BF16 vision projector | Text and images | Yes, text with MTP; projector not downloaded |
| Qwen3.8 27B | unsloth `UD-Q4_K_XL` (16.35 GiB) or `UD-Q8_K_XL` (29.30 GiB) GGUF; optional z-lab DFlash2 draft | Dense text and images | No |
| DeepSeek V4 Flash | antirez `deepseek-v4-gguf`, mixed IQ2/Q2/Q8, 80.76 GiB | Text, with optional DSpark speculation | No |
| EmbeddingGemma 2 | `google/embeddinggemma-2`, BF16 | Text, image, video and audio embeddings on `/v1/embeddings` | No |
| Qwen-Image-2.1 and 2.1 Turbo | BF16 safetensors, about 33 GB | Image generation and editing; non-commercial Qwen Research License | No |
| Qwen3-ASR 1.7B | BF16 safetensors | Speech to text; 0.6B unsupported | No |
| Qwen3-TTS 12Hz 1.7B, CustomVoice, VoiceDesign or Base | BF16 safetensors | Speech from preset voices, a voice description or reference audio; 0.6B unsupported | No |
| MiniMax H3 FL2VA | `MiniMaxAI/MiniMax-H3` safetensors | Text to video with sound, as MP4 | No |

## Strixite 0.7.0

Strixite runs only Qwen3.8-Flash-Next, from its own `wemoh/Qwen3.8-Flash-Next-strixw` weights: the converted model, its n-gram table and a vision tower, all provisioned. Upstream plans no other models or platforms. [README](https://github.com/shawnshekari/strixite/blob/v0.7.0/README.md).
