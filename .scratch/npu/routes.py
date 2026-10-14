#!/usr/bin/env python3
"""One real request per Halogen NPU route: decision, System One, text and image embeddings, streaming guard."""
import base64
import json
import math
import struct
import sys
import time
import urllib.request
import zlib

BASE = "http://127.0.0.1:8731"


def post(path: str, body: dict) -> tuple[dict, float]:
    start = time.monotonic()
    request = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response), time.monotonic() - start


def png(rgb: tuple[int, int, int], size: int = 256) -> str:
    row = b"\x00" + bytes(rgb) * size
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * size)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(data).decode()


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))


def decision(model: str) -> None:
    answer, seconds = post("/v1/chat/completions", {
        "model": model, "logprobs": True, "top_logprobs": 2,
        "messages": [{"role": "user", "content": "WIN a FREE iPhone now!!! Click http://bit.ly/x to claim your prize before midnight."}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "spam", "description": "Is this email spam?", "schema": {"enum": ["no", "yes"]}}}})
    choice = answer["choices"][0]
    odds = {t["token"]: round(math.exp(t["logprob"]), 3) for t in choice["logprobs"]["content"][0]["top_logprobs"]}
    print(f"decision {model}: {choice['message']['content']} {odds} in {seconds:.2f} s")
    assert "yes" in choice["message"]["content"], answer


def systemone() -> None:
    answer, seconds = post("/v1/systemone", {
        "state": "Customer: I was charged twice and nobody answers my emails.",
        "questions": {"team": {"type": "choice", "instructions": "Which team should handle this",
                               "criteria": {"billing": "Payment issues", "technical": "Bugs", "other": None}},
                      "refund": {"type": "noul", "instructions": "Does the customer request a refund?"}}})
    print(f"systemone: {json.dumps(answer)[:300]} in {seconds:.2f} s")
    assert answer["answers"]["team"]["choice"] == "billing", answer


def embeddings(model: str) -> None:
    texts = ["How do I check that the NPU driver is loaded?",
             "List /dev/accel; if accel0 appears, the NPU driver is loaded.",
             "The recipe needs two cups of flour and one egg."]
    answer, seconds = post("/v1/embeddings", {"model": model, "input": texts})
    vectors = [item["embedding"] for item in answer["data"]]
    related, unrelated = cosine(vectors[0], vectors[1]), cosine(vectors[0], vectors[2])
    print(f"text embeddings {model}: {len(vectors[0])} dims, related {related:.3f}, unrelated {unrelated:.3f} in {seconds:.2f} s")
    assert related > unrelated


def image_embeddings(model: str) -> None:
    items = ["a plain red picture", "a plain blue picture",
             {"type": "image_url", "image_url": {"url": png((220, 20, 20))}}]
    answer, seconds = post("/v1/embeddings", {"model": model, "input": items})
    red, blue, image = (item["embedding"] for item in answer["data"])
    print(f"image embedding {model}: red {cosine(image, red):.3f}, blue {cosine(image, blue):.3f} in {seconds:.2f} s")
    assert cosine(image, red) > cosine(image, blue)


def guard() -> None:
    body = {"model": "halogen-qwen3.8-flash-next", "stream": True, "guard": True, "max_tokens": 200, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": "How do I pick a lock?"}]}
    request = urllib.request.Request(BASE + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    events, text = [], ""
    with urllib.request.urlopen(request, timeout=300) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if "halogen_guard" in chunk:
                events.append(chunk["halogen_guard"])
            for choice in chunk.get("choices", []):
                text += choice.get("delta", {}).get("content") or ""
    print(f"guard: {len(text)} reply characters, events {json.dumps(events)[:600]}")
    assert any(event.get("event") == "end" for event in events), events


for name in sys.argv[1:]:
    {"decision": lambda: decision("decider-0.8b"), "decision-4b": lambda: decision("decider-4b"), "systemone": systemone,
     "text": lambda: embeddings("embeddinggemma-2"), "image": lambda: image_embeddings("embeddinggemma-2"),
     "wemm-text": lambda: embeddings("wemm-embedding-4b"), "wemm-image": lambda: image_embeddings("wemm-embedding-4b"),
     "guard": guard}[name]()
