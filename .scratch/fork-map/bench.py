#!/usr/bin/env python3
"""Replay a pi-shaped agent conversation against Halogen and record per-request prompt reuse and latency.

Greedy decode makes both server configurations produce the same replies, so the prompts match request for request.
Assistant turns are sent back the way pi 1.2.0 does: reasoning in reasoning_content, tool arguments as compact JSON.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:8731/v1/chat/completions"
TOOLS = [{"type": "function", "function": {
    "name": "read", "description": "Read a text file from the repository.",
    "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path relative to the repository root"}},
                   "required": ["path"]}}}]
SYSTEM = ("You are a coding assistant working in a local repository. Use the read tool to inspect files before answering. "
          "Answer concisely.\n\n<project_context>\n" + (ROOT / "README.md").read_text() + "\n" + (ROOT / "AGENTS.md").read_text()
          + "\n</project_context>")
FOLLOW_UPS = ["Which of those environment variables would change if the context were reduced to 65536? Answer briefly.",
              "Now compare that with how Gufo receives its context setting. Read what you need."]
TASK = "Read bin/run.sh and explain which environment variables the Halogen container receives and why. Then read bin/models.sh and say how the launcher checks model files."


def read(path: str) -> str:
    target = (ROOT / path).resolve()
    if ROOT not in target.parents or not target.is_file():
        return f"error: no such file {path}"
    return target.read_text()[:20000]


def request(messages: list) -> tuple[dict, dict]:
    body = {"model": "halogen-qwen3.8-flash-next", "messages": messages, "tools": TOOLS, "stream": True,
            "stream_options": {"include_usage": True}, "temperature": 0, "max_tokens": 8192,
            "reasoning_effort": sys.argv[2] if len(sys.argv) > 2 else "medium", "chat_template_kwargs": {"preserve_thinking": True}}
    start = time.monotonic()
    first = None
    reasoning, content, calls, usage, finish = "", "", {}, {}, None
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as response:
        header = response.headers.get("X-Halogen-From", "")
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            usage = chunk.get("usage") or usage
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                if first is None and (delta.get("reasoning_content") or delta.get("content") or delta.get("tool_calls")):
                    first = time.monotonic() - start
                reasoning += delta.get("reasoning_content") or ""
                content += delta.get("content") or ""
                for call in delta.get("tool_calls") or []:
                    slot = calls.setdefault(call["index"], {"id": "", "name": "", "arguments": ""})
                    slot["id"] = call.get("id") or slot["id"]
                    slot["name"] += (call.get("function") or {}).get("name") or ""
                    slot["arguments"] += (call.get("function") or {}).get("arguments") or ""
                finish = choice.get("finish_reason") or finish
    message = {"role": "assistant", "content": content or None}
    if reasoning:
        message["reasoning_content"] = reasoning
    if calls:
        message["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
            "name": c["name"], "arguments": json.dumps(json.loads(c["arguments"] or "{}"), separators=(",", ":"))}}
            for _, c in sorted(calls.items())]
    details = usage.get("prompt_tokens_details") or {}
    return message, {"prompt": usage.get("prompt_tokens"), "cached": details.get("cached_tokens"),
                     "output": usage.get("completion_tokens"), "ttft_s": round(first or 0, 2),
                     "total_s": round(time.monotonic() - start, 2), "from": header, "finish": finish}


def main() -> None:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": TASK}]
    records = []
    for user in [None, *FOLLOW_UPS]:
        if user:
            messages.append({"role": "user", "content": user})
        for _ in range(8):
            message, record = request(messages)
            record["turn"] = len(records)
            records.append(record)
            print(json.dumps(record), flush=True)
            messages.append(message)
            if not message.get("tool_calls"):
                break
            for call in message["tool_calls"]:
                arguments = json.loads(call["function"]["arguments"])
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": read(arguments.get("path", ""))})
    Path(sys.argv[1]).write_text(json.dumps(records, indent=1))


main()
