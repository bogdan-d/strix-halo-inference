// Reject repaired/truncated calls before any tool runs, including sibling calls.
import assert from "node:assert/strict";
import guard from "./strixite_guard.ts";

const handlers = new Map();
guard({ on: (name, handler) => handlers.set(name, handler) });
const emit = (name, event) => handlers.get(name)(event);
const call = (id) => emit("tool_call", { toolCallId: id });
const start = () => emit("message_start", { message: { role: "assistant" } });
const delta = (index, text) => emit("message_update", {
  assistantMessageEvent: { type: "toolcall_delta", contentIndex: index, delta: text },
});
const end = (stopReason, ids) => emit("message_end", {
  message: { role: "assistant", stopReason, content: ids.map((id) => ({ type: "toolCall", id })) },
});

start();
assert.equal(call("missing").block, true);
delta(0, '{"command":');
delta(0, '"echo fixture"}');
end("toolUse", ["complete"]);
assert.equal(call("complete"), undefined);

start();
assert.equal(call("complete").block, true, "Approval must not leak across turns");
delta(0, '{"command":"echo truncated');
delta(1, '{"command":"echo complete"}');
end("toolUse", ["partial", "sibling"]);
assert.equal(call("partial").block, true);
assert.equal(call("sibling"), undefined);

for (const reason of ["length", "error", "aborted", "stop"]) {
  start();
  delta(0, '{"command":"echo complete"}');
  end(reason, ["cut"]);
  assert.equal(call("cut").block, true, reason);
}
console.log("Strict tool-argument completeness and turn-isolation checks passed.");
