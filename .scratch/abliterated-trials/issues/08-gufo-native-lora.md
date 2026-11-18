# 08: Revisit native LoRA loading for Gufo Flash-Next

Status: needs-triage

The goal is to select stock Qwen3.8 Flash-Next weights and a separate GGUF LoRA in the dashboard and let Gufo apply the adapter. Loading it at startup would satisfy the goal. Per-request switching is an optional follow-up.

Defer the decision until a future Gufo or extension release. The current Q4_K_XL and IQ4_XS reflink profiles already work and together use about 1.63 GiB of extra disk. [Local baseline and validation](../../../docs/weight-profiles.md#gufo-huihui-v2-lora-profiles)

## At the next review

- Check whether Gufo or a published extension can load the 2.3 MB Huihui v2 GGUF adapter. Verify coverage separately for the built-in Q4_K_XL provider and the IQ4_XS extension. [Gufo feature request #1247](https://github.com/gufo-org/gufo/issues/1247) · [Extension registry](https://github.com/gufo-org/gufo-extension)
- If support is still missing, compare building a Flash-Next extension, adding support upstream, and maintaining a small Gufo fork. The DeepSeek extension provides a GGUF LoRA implementation to study, and the existing IQ extension owns the IQ4_XS loader. [DeepSeek implementation](https://github.com/franzmoca/ds41-gufo-extension/blob/004f8cc098614663be49dc3073908da00f725c28/lora_adapter.cpp) · [Flash-Next IQ extension](https://github.com/storm1er/flash-next-iq-gufo-extension)
- Record which route is worth pursuing, including staying with reflinks. Weigh dashboard integration, adapter-aware prompt caching, MTP compatibility and maintenance across Gufo releases. The existing merges and matched coding trials provide a reference for a future prototype.
