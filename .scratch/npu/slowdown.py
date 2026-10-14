#!/usr/bin/env python3
"""Flash prefill and decode with the NPU idle and under a sustained NPU load, alternating. argv: MODEL (load) ROUNDS."""
import json
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path

BASE = "http://127.0.0.1:8731"
ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ((ROOT / "README.md").read_text() + (ROOT / "docs/engine-updates.md").read_text()) * 2


def post(body: dict, path: str = "/v1/chat/completions"):
    request = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return urllib.request.urlopen(request, timeout=900)


def flash() -> dict:
    # A fresh nonce at the start keeps every prompt uncached.
    body = {"model": "halogen-qwen3.8-flash-next", "stream": True, "stream_options": {"include_usage": True},
            "temperature": 0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": f"Run {uuid.uuid4()}.\n\n{CONTEXT}\n\nWrite the numbers from one to three hundred in English words, comma-separated."}]}
    start, first, usage = time.monotonic(), None, {}
    with post(body) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            usage = chunk.get("usage") or usage
            if first is None and any(c.get("delta", {}).get("content") for c in chunk.get("choices", [])):
                first = time.monotonic() - start
    total = time.monotonic() - start
    output = usage["completion_tokens"]
    return {"prompt": usage["prompt_tokens"], "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            "prefill_tok_s": round(usage["prompt_tokens"] / first, 1), "ttft_s": round(first, 2),
            "output": output, "decode_tok_s": round((output - 1) / (total - first), 1)}


def load(model: str, stop: threading.Event, counts: list[int]) -> None:
    texts = [f"Passage {i}: {CONTEXT[i * 400:(i + 1) * 400]}" for i in range(8)]
    while not stop.is_set():
        if model.startswith("decider"):
            body = {"model": model, "messages": [{"role": "user", "content": CONTEXT[:6000]}],
                    "response_format": {"type": "json_schema", "json_schema": {
                        "name": "topic", "description": "Is this text about cooking?", "schema": {"enum": ["no", "yes"]}}}}
            post(body).read()
        else:
            post({"model": model, "input": texts}, "/v1/embeddings").read()
        counts[0] += 1


model, rounds = sys.argv[1], int(sys.argv[2])
flash()  # warm up kernels and the lookup table's file cache
for round_ in range(rounds):
    for busy in (False, True):
        stop, counts = threading.Event(), [0]
        worker = threading.Thread(target=load, args=(model, stop, counts)) if busy else None
        if worker:
            worker.start()
            time.sleep(2)
        result = flash()
        stop.set()
        if worker:
            worker.join()
        print(json.dumps({"round": round_, "npu": model if busy else "idle", "npu_requests": counts[0], **result}), flush=True)
