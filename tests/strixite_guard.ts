/** Test-only guard: never execute Pi's repaired or length-cut tool arguments. */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const raw = new Map<number, string>();
  const allowed = new Set<string>();
  pi.on("message_start", (event) => {
    if (event.message.role === "assistant") {
      raw.clear();
      allowed.clear();
    }
  });
  pi.on("message_update", (event) => {
    const update = event.assistantMessageEvent;
    if (update.type === "toolcall_delta") {
      raw.set(update.contentIndex, (raw.get(update.contentIndex) ?? "") + update.delta);
    }
  });
  pi.on("message_end", (event) => {
    if (event.message.role !== "assistant" || event.message.stopReason !== "toolUse") return;
    event.message.content.forEach((block, index) => {
      if (block.type !== "toolCall") return;
      try {
        const args: unknown = JSON.parse(raw.get(index) ?? "");
        if (args && typeof args === "object" && !Array.isArray(args)) allowed.add(block.id);
      } catch {
        // Invalid original JSON must not become executable through Pi's repair.
      }
    });
  });
  pi.on("tool_call", (event) => {
    if (!allowed.has(event.toolCallId)) {
      console.error("strict-arguments: blocked");
      return { block: true, reason: "Missing complete strict-JSON arguments from a successful tool-call response." };
    }
    console.error("strict-arguments: allowed");
  });
}
