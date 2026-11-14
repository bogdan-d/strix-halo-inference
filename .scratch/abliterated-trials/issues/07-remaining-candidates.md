# 07: Maybe try the remaining candidates

**What to build:** Nothing yet. After tickets 01 to 06, decide from their results which of these are still worth a download. Each would follow the same trial checks.

**Blocked by:** 02, 03, 04, 05, 06.

**Status:** needs-triage

| Candidate | Engine | Download | Worth it when |
|---|---|---|---|
| NeosQ `UD-Q4_K_XL` with its MTP head | Gufo | 115.5 GB | The huihui patch (ticket 04) fails its refusal probe, or the same orcarouter abliteration is wanted on every engine. Its author's refusal evidence is thin and tool calling is untested |
| huihui v2 `unsloth-UD-IQ4_XS` folder (October layout) | Gufo with the extension | 87.25 GiB | The patched UD 3.1 `UD-IQ4_XS` (ticket 05) misbehaves and a prebuilt file is wanted for comparison |
| UD 3.1 `UD-IQ3_XXS` on the johandevlabs fork, stock then patched | Gufo 0.33.0 fork | 54.8 GB with the n-gram shard reused, plus the image | The lowest Gufo memory matters (about 64.8 GiB by the fork's README). The fork sits behind a moving tag: pin it by digest and treat it as a separate engine build. Recheck first whether the extension has gained Q6_K token embedding support, which would make the fork unnecessary |
| orcarouter IQ4_XS GGUF, or the ungated wy2pay copy | Halogen as a GGUF | 90.77 GiB | Unlikely: r2's card measured an abliterated IQ4_XS GGUF as slower and larger than r2 |
| johnlockejrr Huihui v1 or v2 HGN bundles | Halogen | about 119 GB each | huihui's abliteration is preferred over orcarouter's after ticket 04. Neither bundle has been loaded in the engine |
| Stock peonist HT43 checkpoint | Halogen | 57.6 GB | Ticket 03 leaves open whether a quality gap comes from HT43 or from the abliteration |

## Comments
