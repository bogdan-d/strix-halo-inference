# Use Qwen3.8 Flash Next with Pi

Use Pi on the host with any engine's local OpenAI Chat Completions endpoint. No chat UI, proxy, provider extension or new Pi package is needed. The configs were checked with Pi 1.1.0, Halogen 0.17.5, Gufo 0.11.0 and Strixite 0.2.3. Strixite's remaining long-context and unrestricted real-project validation limits are in [the trial guide](strixite.md).

## Install the configs

The checked-in [models.json](../config/pi/models.json) registers all three providers at the full native 262,144-token context. [settings.json](../config/pi/settings.json) adds per-model thinking and compaction settings without changing your default provider, model, tools or other models' settings. These files are fragments to merge into Pi's agent directory, normally `~/.pi/agent`. Updating this repository does not modify that live directory. A project `.pi/models.json` is not a supported alternative.

Run the following from this checkout in Bash. If your shell is Fish, enter `bash` first. Existing files are backed up before changes. Matching Halogen, Gufo and Strixite entries are updated to the checked-in profile, while unrelated entries are preserved. Set `PI_CODING_AGENT_DIR` first if you use a different agent directory.

```bash
python - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path

def merge(current, addition):
    for key, value in addition.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            merge(current[key], value)
        else:
            current[key] = value

agent = Path(os.environ.get("PI_CODING_AGENT_DIR", "~/.pi/agent")).expanduser()
agent.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
for name in ("models.json", "settings.json"):
    target = agent / name
    original = target.read_text() if target.exists() else None
    current = json.loads(original) if original is not None else {}
    addition = json.loads((Path("config/pi") / name).read_text())
    merge(current, addition)
    if original is not None:
        backup = agent / f"{name}.backup-{stamp}"
        with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
            file.write(original)
        print(f"Backup: {backup}")
    target.write_text(json.dumps(current, indent=2) + "\n")
    print(f"Updated: {target}")
PY
```

The merge command accepts ordinary JSON. If your existing files contain comments, merge the fragments manually instead. Backups stay in your private agent directory, not this public repository. To undo the installation, restore the printed backups, or remove only the local providers and their matching per-model settings.

Check registration without starting an inference engine:

```bash
pi --offline --list-models qwen3.8
```

You should see `halogen/halogen-qwen3.8-flash-next`, `gufo/qwen3.8-flash-next` and `strixite/qwen3.8-flash-next`. The literal API key `local` is a non-secret placeholder that makes these providers selectable. None of these endpoints requires authentication.

## Start coding with Halogen

Start the engine from this checkout, unless it is already running. Waited startup returns when ready:

```bash
bin/run.sh halogen start --wait
bin/run.sh halogen status
```

Then change to the project you want Pi to work on and launch it there:

```bash
cd /path/to/your/project
pi --provider halogen --model halogen-qwen3.8-flash-next --thinking xhigh
```

Pi now reads and edits that project using the local model. For example, ask it to inspect a function, fix a bug and run the relevant tests. The CLI thinking flag is explicit here, but the installed per-model settings also select `xhigh` for new sessions.

For a read-only first check in a project:

```bash
pi --provider halogen --model halogen-qwen3.8-flash-next --thinking xhigh \
  --no-extensions --no-skills --no-prompt-templates --no-context-files \
  --no-approve --no-mcp --tools read --no-session --print \
  "Read README.md and summarize what this project does. Do not modify files."
```

The limited tool selection above is for that check, not ordinary coding. Normal launches retain your existing Pi tools, skills and extensions. In an already running Pi session, `/model` reloads `models.json`. Select the engine's model, then use `/thinking` to select the level. Restart Pi after installing the settings fragment to load its startup and compaction settings reliably.

## Switch to Gufo

Finish or cancel the current Pi request before switching. Stop Halogen from this checkout, start Gufo and wait for readiness:

```bash
bin/run.sh halogen stop
bin/run.sh gufo start --wait
bin/run.sh gufo status
```

From the target project:

```bash
pi --provider gufo --model qwen3.8-flash-next --thinking xhigh
```

Do not run the engines together. The launchers enforce this restriction. Each uses one active inference slot with MTP enabled. Do not launch parallel coding agents against the same engine for the initial comparison. Pi does not start or stop the containers for you.

## Select Strixite

Stop the active engine and verify memory release first, then start Strixite:

```bash
bin/run.sh gufo stop
bin/run.sh strixite start --wait
bin/run.sh strixite status
```

Use `bin/run.sh halogen stop` instead if Halogen is active. The installed provider is `strixite`, model `qwen3.8-flash-next`, at localhost:5300. Select it with `/model`, or use `pi --provider strixite --model qwen3.8-flash-next --thinking xhigh`. The per-model default is xhigh, with the same 256K context and compaction budgets as the existing engines. Ordinary Pi tools still have host user permissions. Installing this profile does not install the test-only strict JSON guard or Bubblewrap. Use [the guarded synthetic runner](strixite.md#api-tools-cancellation-and-guarded-pi-results) to verify coding tools without exposing real projects.

Strixite supports automatic tool selection but rejects named or required tool choice. It also rejects nonzero presence and frequency penalties and repetition penalties other than 1. Its off profile therefore uses presence penalty 0, unlike the Halogen/Gufo model-card preset. No other provider's sampling is changed.

## Model settings and their limits

This is the model publisher's recommended coding profile, not a locally benchmarked optimum. Qwen's coding evaluation uses temperature `1.0` and top-p `0.95`. Arbitrarily lowering the temperature for coding or forcing greedy decoding would depart from that recommendation.

| Setting | Thinking profile | `--thinking off` profile |
|---|---|---|
| Temperature | `1.0` | `0.7` |
| Top-p | `0.95` | `0.8` |
| Top-k | `20` | `20` |
| Min-p | `0.0` | `0.0` |
| Presence penalty | `0.0` | `1.5` for Halogen/Gufo, `0.0` for Strixite |
| Repetition penalty | `1.0` | `1.0` |
| Frequency penalty | `0.0`, neutral engine default | `0.0`, neutral engine default |
| Preserve thinking | `true` | `true` |
| Total completion limit | `16384` | `16384` |

`reasoning: true` lets Pi receive and replay the servers' `reasoning_content` as thinking blocks. `preserve_thinking: true` keeps that reasoning in subsequent rendered turns, which Qwen recommends for agent continuity and prompt-cache reuse. Thinking consumes context and completion tokens even when its display is hidden.

Pi sends `reasoning_effort` through the OpenAI compatibility configuration. The map explicitly sends `none` for Pi's `off` setting. Simply marking the model as nonreasoning would not reliably disable the engine's default thinking. The profiles expose only `off`, `low`, `medium` and `xhigh`, matching the engines' nonthinking mode and three distinct effort levels. Pi's native `thinkingLevelMap` entries for `minimal`, `high` and `max` are `null`, which removes them from `/thinking` and thinking-level cycling instead of presenting duplicate aliases. Omitting those entries is insufficient because Pi enables some unspecified levels by default. Existing unsupported CLI or saved levels are clamped by Pi to a supported level. Defaults, sampling and completion limits are unchanged.

Keep `xhigh` for substantial coding tasks. Use `--thinking medium` or `--thinking low` when you want to trade reasoning effort for responsiveness. Use `--thinking off` for direct, simple tasks. Pi automatically applies the corresponding sampling preset. Changing effort within a conversation can invalidate its cached prefix, so prefer a consistent level during an engine comparison.

In the [local routine-coding comparison](thinking-comparison.md), `medium` was faster in all eight pairs and both levels passed the fixed checks. Try it for small, well-specified edits with good checks. The sample covers only two short synthetic tasks, not difficult debugging or long-context coding. The defaults remain `xhigh`, and `low` was not tested.

The 16,384-token completion limit is an operational starting point for reasoning plus tool calls or final text. It is not 16K of reasoning followed by another 16K of output. Halogen reserves answer room when closing an overlong reasoning block. Gufo has no separate numeric thinking budget or guaranteed answer-room transition, so an unusually long reasoning phase can hit the total limit without an answer. Do not configure a Halogen-style thinking-budget field for Gufo. These profiles do not impose a separate numeric thinking cap on either engine.

All three models advertise `contextWindow: 262144`, matching the launcher's full native 256K allocation. The compaction overrides reserve 16,384 tokens and retain approximately 32,768 recent tokens. Automatic compaction starts when estimated context exceeds 245,760 tokens, leaving room for the configured completion. System instructions, tool declarations, tool results and preserved thinking count toward that context. The 16K completion cap limits one response, not the conversation's context capacity.

If you previously installed the 32K profiles, explicitly update both local providers' `contextWindow` to `262144` in your agent directory's `models.json`. Also update their `compaction.modelOverrides` entries to retain `32768` recent tokens in `settings.json`, or rerun the merge command above when you want to apply the complete checked-in profiles. Restart the engine to resize its context, open `/model` to reload model metadata and restart Pi to reload settings.

If you override the launcher with a smaller `CONTEXT`, reduce the matching installed model's `contextWindow` too and choose compaction budgets that fit that smaller capacity. Do not advertise more context in Pi than the server allocated. Near-capacity prompt processing, long-context quality and throughput remain unbenchmarked on this host. The Strixite profile lists `image` input, so Pi sends pasted or attached images to it; this needs Strixite's default `VISION=on`. Halogen and Gufo stay text only until their vision files are configured.

## Troubleshooting

- **Connection refused:** the selected container is stopped, crashed or listening on the other engine's port. Check `bin/run.sh ENGINE status` and `bin/run.sh ENGINE logs` from this checkout.
- **Provider missing:** check the actual agent directory and the merge result. Open `/model` to reload providers, or restart Pi. There is no `/login` step for these local endpoints.
- **Empty answer or length limit:** reasoning may have consumed the completion budget. Try a fresh session with a lower effort, inspect server logs and avoid assuming Gufo supports a separate thinking cap.
- **Context overflow:** use `/compact` or a new session and verify Pi's context metadata matches the launcher. Switching from a much larger remote-model session can bring too much history into the local model.
- **Unexpected extensions or too much startup context:** first use the minimal read-only command above. Reintroduce your normal resources after confirming the provider connection.
- **Schema response fails on Halogen:** its JSON-schema constrained output currently requires greedy sampling. Ordinary Pi function-tool requests work with this sampled coding profile, but an extension requesting `response_format` may need different settings.

Only inference is containerized. Pi and its tools still run with your host user permissions. A local endpoint and a read-only weights mount do not sandbox model-generated shell commands or edits. Review changes and keep credentials out of the coding workspace where practical.

## Sources

- [Qwen3.8-Flash-Next model card and best practices](https://huggingface.co/Qwen/Qwen3.8-Flash-Next#best-practices), checked October 10, 2026.
- [Halogen 0.17.5 agent integration, sampling and reasoning controls](https://github.com/peonist-ai/halogen-flash-server/blob/v0.17.5/README.md).
- [Gufo 0.11.0 server contract](https://github.com/gufo-org/gufo/blob/v0.11.0/docs/SERVER.md).
- [Pi compatible endpoints and per-thinking-level sampling](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md).
- [Pi settings and per-model compaction](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md).
