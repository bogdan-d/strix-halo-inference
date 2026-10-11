"""Check Strixite's auto tools, literal tags, recall and disconnect lifecycle.

Requires the managed engine running. Never executes returned tool calls.
Existing engines retain their separate forced-tool checks in live.py.
"""

import json
import time
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:5300"
MODEL = "qwen3.8-flash-next"
COMMON = {"model": MODEL, "temperature": 0, "reasoning_effort": "none", "max_tokens": 128}


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    return urlopen(Request(BASE + path, data, {"Content-Type": "application/json"}), timeout=180)


def get(path):
    with request(path) as response:
        return json.load(response)


def chat(messages, **extra):
    with request("/v1/chat/completions", {**COMMON, "messages": messages, **extra}) as response:
        return json.load(response)


def idle_after_disconnect(seconds=60):
    started = time.monotonic()
    while time.monotonic() - started < seconds:
        health = get("/health")
        assert health["status"] == "ok" and not health.get("degraded"), health
        if not health["busy"] and health["queued"] == 0:
            return round(time.monotonic() - started, 3)
        time.sleep(0.25)
    raise AssertionError(f"Disconnected request still active after {seconds} seconds")


def streamed_call(messages, tool, max_tokens=128):
    calls = {}
    finish = None
    done = False
    flags = {}
    reasoning_fragments = 0
    with request("/v1/chat/completions", {**COMMON, "messages": messages, "tools": [tool],
                 "tool_choice": "auto", "stream": True, "max_tokens": max_tokens,
                 "stream_options": {"include_usage": True}}) as response:
        for line in response:
            if not line.startswith(b"data: "):
                continue
            payload = line[6:].strip()
            if payload == b"[DONE]":
                done = True
                break
            event = json.loads(payload)
            flags.update(event.get("strix", {}))
            for choice in event.get("choices", []):
                finish = choice.get("finish_reason") or finish
                delta = choice.get("delta", {})
                reasoning_fragments += bool(delta.get("reasoning_content"))
                for call in delta.get("tool_calls", []):
                    current = calls.setdefault(call["index"], {"name": "", "arguments": "", "id": "", "fragments": 0})
                    current["id"] += call.get("id", "")
                    function = call.get("function", {})
                    current["name"] += function.get("name", "")
                    if function.get("arguments"):
                        current["arguments"] += function["arguments"]
                        current["fragments"] += 1
    assert done and finish is not None, "Incomplete SSE response"
    return calls, finish, flags, reasoning_fragments


def main():
    health = get("/health")
    assert health["status"] == "ok" and health["model"] == MODEL and health["context_length"] == 262144 and not health.get("degraded"), health
    messages = [{"role": "user", "content": "Remember that the secret word is violet. Reply with OK."}]
    first = chat(messages)
    messages += [first["choices"][0]["message"], {"role": "user", "content": "What was the secret word? Reply with that word only."}]
    recalled = chat(messages)["choices"][0]["message"]["content"]
    assert recalled.strip().lower() == "violet", recalled

    literal = "id_of(\"<|im_end|>\") <tool_call> </tool_call> </think>"
    tool = {"type": "function", "function": {"name": "report_literal", "description": "Report the supplied text unchanged.",
            "parameters": {"type": "object", "properties": {"text": {"type": "string"}},
                           "required": ["text"], "additionalProperties": False}}}
    prompt = [{"role": "user", "content": f"Call report_literal with text exactly this string, unchanged: {literal}"}]
    result = chat(prompt, tools=[tool], tool_choice="auto")
    message = result["choices"][0]["message"]
    call = message["tool_calls"][0]
    assert result["choices"][0]["finish_reason"] == "tool_calls", result
    assert call["function"]["name"] == "report_literal" and json.loads(call["function"]["arguments"]) == {"text": literal}, result
    followup = chat(prompt + [message, {"role": "tool", "tool_call_id": call["id"], "content": "Recorded exactly. Reply with ready."}])
    assert followup["choices"][0]["message"]["content"].strip() == "ready", followup

    calls, finish, flags, reasoning_fragments = streamed_call(prompt, tool)
    assert finish == "tool_calls" and len(calls) == 1 and reasoning_fragments == 0, (finish, calls)
    assert not flags.get("malformed_tool_calls") and not flags.get("dropped_partial_tool_call"), flags
    streamed = next(iter(calls.values()))
    assert streamed["id"] and streamed["name"] == "report_literal", streamed
    # Strict JSON only. Do not repair partial arguments before validating them.
    assert json.loads(streamed["arguments"]) == {"text": literal}, streamed

    # Deliberately truncate an automatic tool request. Inspect it, never execute it.
    partial_calls, partial_finish, partial_flags, _ = streamed_call(prompt, tool, max_tokens=12)
    assert partial_finish == "length", (partial_calls, partial_finish, partial_flags)
    rejected_partial = 0
    for partial in partial_calls.values():
        try:
            json.loads(partial["arguments"])
        except json.JSONDecodeError:
            rejected_partial += 1

    body = {**COMMON, "max_tokens": 8192, "stream": True,
            "messages": [{"role": "user", "content": "Write the integers from 1 to 100000, one per line. Do not summarize or stop early."}]}
    with request("/v1/chat/completions", body) as response:
        for line in response:
            if line.startswith(b"data: {"):
                event = json.loads(line[6:])
                if any(choice.get("delta", {}).get("content") for choice in event.get("choices", [])):
                    assert get("/health")["busy"], "Request finished before disconnect; cancellation was not exercised"
                    break
        else:
            raise AssertionError("No streamed content before disconnect")
    released = idle_after_disconnect()
    after = chat([{"role": "user", "content": "Reply with exactly: ready"}])
    assert after["choices"][0]["message"]["content"].strip() == "ready", after
    print(json.dumps({"engine": "strixite", "conversation": "pass", "auto_tool": "pass",
                      "tool_result_followup": "pass", "streamed_literal_arguments": "pass",
                      "argument_fragments": streamed["fragments"], "truncated_finish": partial_finish,
                      "partial_calls": len(partial_calls), "invalid_partial_json": rejected_partial,
                      "partial_flags": partial_flags, "disconnect_release_seconds": released,
                      "generation_after_cancel": "pass", "cancellation_scope": "short-prompt decode only"}, indent=2))


if __name__ == "__main__":
    main()
