# Medium versus xhigh for routine coding

On this host, `medium` finished faster in all eight paired comparisons, and both levels passed all fixed checks. Try `medium` for small, well-specified edits with good checks. Keep `xhigh` available for difficult debugging, planning and larger changes. This is an exploratory comparison of two synthetic tasks, not evidence of equal coding quality in general. Neither the checked-in defaults nor the live Pi defaults were changed.

## Results

Pi 1.1.0 used Halogen 0.17.5 and Gufo 0.11.0 with the existing image and model pins, 262,144-token capacity and MTP enabled. Each engine completed two trials per task per effort level, for 16 measured trials. Mean time includes Pi process startup, inference and tool execution, but excludes engine loading and the independent final check.

These measurements predate the shared Bubblewrap boundary described below. They used temporary configuration and workspaces but ran tools with host user permissions, so these are not sandboxed timing results. A subsequent [sandboxed three-engine comparison](coding-comparison.md) completed 36 trials on the same tasks, including off, medium and xhigh, with matched sampling and the strict argument guard. All passed; medium again finished faster than xhigh in every paired case. Its settings and model-visible paths differ, so do not interpret it as a controlled timing comparison with this historical matrix.

| Engine | Effort | Passed | Mean task time | Total tool calls | Output tokens across four trials | Tool results reporting errors |
|---|---|---|---|---|---|---|
| Halogen | medium | 4/4 | 34.59 s | 25 | 7,892 | 0 |
| Halogen | xhigh | 4/4 | 83.60 s | 37 | 18,969 | 2 |
| Gufo | medium | 4/4 | 39.11 s | 23 | 6,194 | 0 |
| Gufo | xhigh | 4/4 | 69.76 s | 28 | 11,745 | 1 |

Medium's mean task time was approximately 59% lower on Halogen and 44% lower on Gufo. Output tokens include reasoning and other generated content, not just the final answer. Tool errors are intermediate tool results, not failed final tasks. All trials ended normally with unchanged checks and passing independent verification. No trial timed out or reported a length, error or aborted assistant stop reason.

| Engine | Task | Medium trial times | Xhigh trial times |
|---|---|---|---|
| Halogen | Environment parser fix | 37.90 s, 18.29 s | 45.27 s, 101.42 s |
| Halogen | CSV CLI feature | 50.23 s, 31.94 s | 81.11 s, 106.61 s |
| Gufo | Environment parser fix | 29.33 s, 26.33 s | 59.86 s, 59.32 s |
| Gufo | CSV CLI feature | 53.75 s, 47.05 s | 80.53 s, 79.34 s |

## Tasks and controls

- **Environment parser fix:** repair splitting and quote handling, preserve literal values, validate keys and malformed assignments, and retain duplicate-key behavior. Checks exercise embedded equals signs, hashes, whitespace, empty values and invalid input.
- **CSV CLI feature:** add a minimum-duration filter through the CLI and summarizer, retain sorted grouped output, validate even filtered-out rows, and reject invalid input without a traceback or partial JSON. Checks cover the direct function and actual CLI subprocesses.
- Each trial started from the same source files and checks in a fresh workspace. The original checks were executed independently after Pi finished, and changes to the workspace's check file would fail the trial. Public fixtures and exact prompts are in [thinking_tasks.py](../tests/thinking_tasks.py).
- Sampling stayed at temperature 1.0, top-p 0.95, top-k 20, min-p zero, neutral penalties and preserved thinking. The completion cap stayed at 16,384 tokens. No fixed seed was imposed. Only the requested thinking effort differed within a pair.
- The first repeat used medium then xhigh for each task. The second reversed that order. Halogen ran before Gufo, one engine at a time. These results compare effort within each engine, not pure engine performance across different weight formats.
- Each engine started with its own empty temporary disk-cache directory. In-memory and disk prompt caches remained enabled across its trials, and the OS file cache was not flushed. Fresh workspace paths differ, while tool instructions and parts of the prompt can still share prefixes. This is not a cold-cache experiment.
- Pi reported aggregate cached input of 57,240 tokens for Halogen medium, 132,909 for Halogen xhigh, 47,197 for Gufo medium and 71,803 for Gufo xhigh. These are sums across assistant turns, not unique context sizes. Longer tool loops naturally reread more cached history, so the totals are not a cache-efficiency ranking.
- The host remained on the balanced power profile with the powersave CPU governor. There was no exclusive control of desktop activity, clocks or temperature. User extensions, skills, context files and MCP were disabled to isolate the normal read, edit, write and bash tool loop.

A preflight invocation was discarded after a harness reporting error. The complete measured matrix then started with new temporary caches. Two repeats per condition are too few for a statistical performance claim. These short tasks do not test near-capacity context, large repositories, architectural judgment, security review or the user's full extension stack. Passing the checks establishes those cases, not every possible edge case or maintainability property.

## Select effort in Pi

From the project you want to edit, use an explicit level for the current invocation:

```bash
pi --provider halogen --model halogen-qwen3.8-flash-next --thinking medium
pi --provider gufo --model qwen3.8-flash-next --thinking medium
```

Use `--thinking xhigh` instead for substantial or ambiguous work. Inside Pi, `/thinking` selects the current level. Do not save a new startup level unless you want to change the default. Changing effort in an existing conversation can invalidate cached prefixes, so use fresh sessions when comparing levels.

## Repeat the comparison

Stop any managed inference engine first. Run from this checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/pi_sandbox.py
PYTHONDONTWRITEBYTECODE=1 python tests/thinking.py --self-check
PYTHONDONTWRITEBYTECODE=1 python tests/thinking.py --repeats 2
```

The sandbox check is offline and exercises actual hidden paths, environment clearing, writable workspace access, immutable settings and failure when Bubblewrap is missing. The thinking self-check is also offline. It verifies that both original task implementations fail their acceptance checks inside the sandbox and that event accounting retains truncation and tool-call information. The comparison requires Pi, Bubblewrap, this host's existing Homebrew installation, rootless Podman and the already downloaded pinned weights. It manually starts and stops each engine at 256K with MTP, refuses to run while a managed engine is active, and prints JSON summary records rather than raw conversations. Each Pi invocation has a ten-minute limit. Two repeats produce 16 trials and can take many minutes.

Temporary Pi configuration, workspaces and engine caches live in a uniquely named directory under the ignored `results` directory on disk, not in the normal agent directory or normal engine caches. They are removed after the owned containers stop. A cleanup failure with an engine still running retains temporary state and reports its path rather than deleting mounted data. The live Pi models and settings are checked for byte-for-byte preservation. Existing weights and normal engine caches are not modified by the harness.

Each fresh host workspace is presented at the stable sandbox path `/workspace`. That changes model-visible paths and potential prefix-cache reuse from the historical host-path runs, so future sandboxed timings should not be treated as directly matched repetitions of the published matrix.

All model-driven Pi processes and independent acceptance checks now run inside the shared [Bubblewrap boundary](../tests/pi_sandbox.py), also used by the Strixite coding check. The current synthetic workspace is the only writable host mount. Temporary model/settings inputs are mounted read-only into an ephemeral agent directory, which allows Pi to create its own locks and empty runtime authentication file without exposing host credentials. Only `/usr` and the existing Homebrew software tree are available read-only. Host home directories, live Pi settings, repositories, weights, inference caches and GPU devices are not mounted. Home, `/tmp`, and runtime agent state are ephemeral, and the environment is cleared. There is no unsandboxed fallback if Bubblewrap or the preflight fails. The fixed acceptance checks remain protected from agent edits and execute imported model-written code inside the same boundary.

Host networking remains shared to reach localhost inference, so this is filesystem and process isolation, not a network sandbox. It does not authorize exposing real projects or credentials to the model. Real model-driven runs through this boundary passed in the subsequent [three-engine comparison](coding-comparison.md). Review fixtures before running them, and do not replace public tasks with private source or prompts and then publish output or conversation artifacts.
