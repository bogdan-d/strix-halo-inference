"""Exercise a running local engine's conversation, tools and disconnect lifecycle."""

import argparse
import json
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("halogen", "gufo"))
    args = parser.parse_args()
    base = "http://127.0.0.1:" + ("8731" if args.engine == "halogen" else "8080")

    def request(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(base + path, data, {"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=180)

    def get(path):
        with request(path) as response:
            return json.load(response)

    model = get("/v1/models")["data"][0]["id"]
    common = {"model": model, "temperature": 0, "max_tokens": 128,
              "chat_template_kwargs": {"enable_thinking": False}}

    def chat(messages, **extra):
        with request("/v1/chat/completions", {**common, "messages": messages, **extra}) as response:
            return json.load(response)

    messages = [{"role": "user", "content": "Remember that the secret word is violet. Reply with OK."}]
    first = chat(messages)
    messages += [first["choices"][0]["message"],
                 {"role": "user", "content": "What was the secret word? Reply with that word only."}]
    second = chat(messages)
    assert "violet" in second["choices"][0]["message"]["content"].lower(), second
    tool = {"type": "function", "function": {"name": "report_ready", "description": "Report readiness.",
            "parameters": {"type": "object", "properties": {"status": {"type": "string", "enum": ["ready"]}},
                           "required": ["status"], "additionalProperties": False}}}
    result = chat([{"role": "user", "content": "Call report_ready with status ready."}],
                  tools=[tool], tool_choice={"type": "function", "function": {"name": "report_ready"}})
    call = result["choices"][0]["message"]["tool_calls"][0]["function"]
    assert call["name"] == "report_ready" and json.loads(call["arguments"]) == {"status": "ready"}, result

    # Native auto-tool streams can split arguments across deltas. Inspect, never execute.
    calls = {}
    finish = None
    done = False
    fragments = 0
    with request("/v1/chat/completions", {**common, "stream": True, "tools": [tool],
                 "tool_choice": "auto", "messages": [{"role": "user", "content": "Call report_ready with status ready."}]}) as stream:
        for line in stream:
            if not line.startswith(b"data: "):
                continue
            payload = line[6:].strip()
            if payload == b"[DONE]":
                done = True
                break
            for choice in json.loads(payload).get("choices", []):
                finish = choice.get("finish_reason") or finish
                for delta in choice.get("delta", {}).get("tool_calls", []):
                    current = calls.setdefault(delta["index"], {"name": "", "arguments": "", "id": ""})
                    current["id"] += delta.get("id", "")
                    function = delta.get("function", {})
                    current["name"] += function.get("name", "")
                    current["arguments"] += function.get("arguments", "")
                    fragments += bool(function.get("arguments"))
    assert done and finish == "tool_calls" and len(calls) == 1, (done, finish, calls)
    streamed = next(iter(calls.values()))
    assert streamed["id"] and streamed["name"] == "report_ready", streamed
    assert json.loads(streamed["arguments"]) == {"status": "ready"}, streamed

    body = {**common, "max_tokens": 8192, "stream": True,
            "messages": [{"role": "user", "content": "Write the integers from 1 to 100000, one per line. Do not summarize or stop early."}]}
    with request("/v1/chat/completions", body) as stream:
        for line in stream:
            if line.startswith(b"data: {"):
                event = json.loads(line[6:])
                if any(c.get("delta", {}).get("content") for c in event.get("choices", [])):
                    break
        else:
            raise AssertionError("Stream ended before producing content")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if args.engine == "halogen":
            idle = get("/health")["in_flight"] == 0
        else:
            idle = all(slot["state"] == 0 for slot in get("/slots"))
        if idle:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("Disconnected request did not release its slot within 20 seconds")
    followup = chat([{"role": "user", "content": "Reply with exactly: ready"}])
    assert followup["choices"][0]["message"]["content"].strip() == "ready", followup
    print(json.dumps({"engine": args.engine, "model": model, "conversation": "pass", "tool_call": "pass",
                      "streamed_auto_tool": "pass", "argument_fragments": fragments,
                      "disconnect_slot_release": "pass", "generation_after_cancel": "pass",
                      "followup_timings": second.get("timings")}, indent=2))


if __name__ == "__main__":
    main()
