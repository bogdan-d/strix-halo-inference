# NPU models beside the Flash model

## Goal

Use the Ryzen AI NPU for small helper models that run beside the main Qwen3.8 Flash model, without taking GPU time or much of its memory. Decide which helpers are worth keeping before anything is enabled by default.

## Current state (October 14, 2026)

- `bin/run.sh` passes `/dev/accel/accel0` to Halogen, Gufo and Strixite. All three started, passed their live checks and stopped cleanly with it. No engine loads an NPU model.
- Only Halogen serves NPU models (0.18.3). Gufo 0.15.0 and Strixite 0.2.4 have no NPU code upstream. The device is passed to them only so later releases need no launcher change.
- The files below are downloaded and hash-verified under `/home/bogdan/models/npu/<id>/`, which Halogen reads as `/models/npu`. `config/npu-files.tsv` lists them, and `bin/npu-manifest.sh` derives that list from the record inside the pinned Halogen image.
- Host: `amdxdna` loaded, NPU firmware present, `iommu=pt` (the NPU needs the IOMMU on, which it is). XRT is not installed. The GPU fabric clock is `auto`, not held.

| Model | Task and route | Memory beside Flash (publisher) | Files |
|---|---|---|---|
| `decider-0.8b` | Decisions: a text plus 2 to 10 options gives every option's probability in one pass. `/v1/chat/completions` with a `response_format` enum, or `/v1/systemone` | "a few GB" with the default set | 3.0 GB |
| `decider-4b` | Same as above, better on harder questions, a little slower | about 5 GB | 6.1 GB |
| `embeddinggemma-2` | Text, image and audio embeddings in one 768-dimension space, `/v1/embeddings` | about 1.1 GB | 1.2 GB |
| `wemm-embedding-4b` | Text and image embeddings, `/v1/embeddings`. Runs on `decider-4b`'s NPU program | not stated | 6.1 GB |
| `qwen3guard-stream-0.6b` | Watches a Flash reply as it streams and labels it Safe, Unsafe or Controversial. Opt-in per request with `"guard": true`. Never stops or changes the reply | about 0.8 GB | 0.8 GB |
| `qwen3-embedding-0.6b` (`devices/` only) | NPU program that the streaming guard runs on. Its own weights were not downloaded | | 0.1 GB |

The Flash model itself takes 81.4 GiB and leaves about 30.6 GiB of host memory at native context. The publisher says Flash runs somewhat slower while the NPU works, because both share the memory bus and the chip's power budget.

## Prerequisites (host changes, need explicit approval)

1. **XRT with its NPU plugin.** Install `xrt` and `xrt-plugin-amdxdna` (2.21.75, CachyOS repositories). Halogen loads three host libraries inside its container, so they must not need a newer C or C++ runtime than the image. Checked without installing: they need at most `GLIBC_2.38` and `GLIBCXX_3.4.32`, below the image's glibc 2.41 and `GLIBCXX_3.4.33`, and their other dependencies are present in the image. Halogen's docs name AMD XRT 2.25 and Ubuntu's XRT 2.21 as tested; Arch builds are not named.
2. **A held GPU fabric clock.** On Strix Halo, GPU and NPU work at the same time can hang the machine or corrupt NPU results while that clock changes speed. Rootless Podman cannot hold it, so Halogen refuses to start NPU models until a root systemd unit from its repository (`deploy/host/halogen-fabric-clock`) holds it at every boot. It costs about a watt. `HALOGEN_NPU_WITH_GPU=1` skips the check and accepts that risk; do not use it.

## Open decisions

- **Which helpers earn their memory?** See the candidate uses below. Loading all five costs well over 10 GB beside Flash.
- **Opt-in or always on?** One `NPU_MODELS` launcher setting, unset by default, keeps Halogen exactly as today. Otherwise pick a fixed set.
- **Flash speed cost.** How much decode and prefill slow down while the NPU is busy, measured, not assumed.
- **Gufo and Strixite.** Recheck at each update whether either gained NPU support.

## Candidate uses

- **Search over local text and screenshots.** `embeddinggemma-2` or `wemm-embedding-4b` could back a semantic `recall` for the agent-memory MCP server, project or document search for Pi, or image search over screenshots. Needs a client and an index; nothing here provides one yet.
- **Cheap routing and triage.** `decider-0.8b` or `decider-4b` can answer fixed-choice questions in one pass: which thinking level a prompt needs, whether a request is a question or a change, or how to label an incoming ticket. It is useful where a Pi extension or script would otherwise ask the Flash model.
- **Reply watching.** `qwen3guard-stream-0.6b` reports risky stretches of a reply without changing it. It has little value for single-user local coding, but could flag replies when a model is exposed to untrusted input.

## Upkeep

Halogen checks each NPU file against the record in its image and refuses a mismatch. The models volume is read-only, so Halogen cannot fetch replacements itself. After a Halogen pin change, run `bin/npu-manifest.sh`, review the diff of `config/npu-files.tsv`, then run `bin/models.sh download npu`. Files no longer listed stay on disk until removed by hand.

## Tickets

- [01: Install XRT and hold the fabric clock](issues/01-host-prerequisites.md)
- [02: Opt-in NPU models in the launcher](issues/02-launcher-opt-in.md)
- [03: First NPU validation and Flash slowdown](issues/03-first-validation.md)
- [04: Choose the helpers and their clients](issues/04-choose-uses.md)
