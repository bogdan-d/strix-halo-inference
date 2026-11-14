# Upstream issue for gufo-org/gufo

Status: filed November 14 as https://github.com/gufo-org/gufo/issues/1232. Checked for duplicates first: none open or closed (#383 covers leaked closing framing, #619 `tool_choice: "required"`). Nothing on `main` after v0.34.0 (`800ce3280`) touches it.

---

**Title:** serve: `tool_choice: "none"` in a conversation with earlier tool calls returns raw `<tool_call>` markup as `content`

## Summary

When a request sets `tool_choice: "none"` and its history already holds an assistant tool call, Flash-Next often answers with a new tool call written as text. The server neither parses nor suppresses it, so the client receives raw `<tool_call>…</tool_call>` markup in `message.content` with `finish_reason: "stop"`. Open WebUI 0.13 sends exactly this request to end a tool loop (after a failed or repeated call, or at its iteration limit), so such chats can end on XML.

## Repro

Gufo 0.34.0 (`ghcr.io/gufo-org/toolboxes/gufo-runtime@sha256:49b1fce4…`, revision `2845939b2a7d`) and 0.33.0, Strix Halo, `gufo serve --sessions 1 llm` with `unsloth/Qwen3.8-Flash-Next-GGUF` `UD-Q4_K_XL`, `--context 262144 --speculative mtp` with the shared Q8_0 MTP head.

```sh
curl -s localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "qwen3.8-flash-next", "temperature": 0.7, "max_tokens": 200,
  "chat_template_kwargs": {"enable_thinking": false},
  "tool_choice": "none",
  "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Get the weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}],
  "messages": [
    {"role": "user", "content": "What'\''s the weather in Paris and in Rome?"},
    {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function",
      "function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"}}]},
    {"role": "tool", "tool_call_id": "c1", "content": "error: weather service unavailable"}]}'
```

Observed, 3 of 3 runs on both versions:

```json
"message": {"role": "assistant", "content": "<tool_call>\n<function=get_weather>\n<parameter=city>\nRome\n</parameter>\n</function>\n</tool_call>"},
"finish_reason": "stop"
```

Expected: a prose answer, no `tool_calls`, and no tool-call markup in `content`.

## Cause, as far as I can read it

For `kNone`, the Qwen runners render the prompt without the tool definitions (`src/models/qwen38_flash_next/runner.cpp`, `RenderQwenPrompt` / `PrepareQwenPrompt`), `constrained_tools` is false (`src/cli/serve/openai_chat.cpp`), and no grammar or tool-call parsing applies (`src/cli/serve/text_model_runner.cpp`). The history still renders the earlier assistant call in the `<tool_call>` format, so the model imitates it, and nothing stops or strips the opener.

## Possible fixes

- Ban the tool-call opener token(s) while sampling under `tool_choice: "none"`, so the model has to answer in prose.
- Or parse the reply as usual and drop or refuse a call that `none` forbids, rather than returning it as text.

For comparison, Halogen fixed the same symptom in 0.20.4 (peonist-ai/halogen-flash-server#253): with `tool_choice: "none"` in a conversation that holds tool calls it now answers in prose on the chat, Responses and Messages endpoints. On the same request it returned prose 3 of 3 times.
