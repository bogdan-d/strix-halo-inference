#!/usr/bin/env python3
"""Inspect the Inference WebView. Start bin/desktop.sh run --inspect first.
Standard library only. WebKit inspector protocol, not CDP; input is synthetic.
  tests/browser.py desktop-check                 native IPC fixture
  tests/browser.py desktop-window-check          native F11/restoration (--agent-debug build)
  tests/browser.py desktop-memory                charts/logs/minimized process-tree measurements
  tests/browser.py close @main                   request a normal close (busy guard still applies)
  tests/browser.py views
  tests/browser.py eval @main file.js|-
  tests/browser.py shot @main cache/test/view.png
  tests/browser.py console @main [seconds]
  tests/browser.py network @main seconds [reload|file.js|-]
  tests/browser.py click @main selector|x y
  tests/browser.py drag @main x1 y1 x2 y2
  tests/browser.py type @main text [selector]
  tests/browser.py key @main key
  tests/browser.py inspect @main Domain.method ['{params}'] ...
One command at a time per view. No trusted input, network history or response bodies.
"""
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

class WebSocket:
    """The little of RFC 6455 that DevTools needs: masked text frames out, text frames in."""

    def __init__(self, url: str) -> None:
        parts = urllib.parse.urlparse(url)
        self.socket = socket.create_connection((parts.hostname, parts.port), timeout=900)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall((f"GET {parts.path} HTTP/1.1\r\nHost: {parts.hostname}:{parts.port}\r\nUpgrade: websocket\r\n"
                             f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            head += self.read(1)
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise SystemExit(head.decode(errors="replace"))

    def send(self, text: str) -> None:
        data, mask = text.encode(), os.urandom(4)
        size = len(data)
        length = bytes([0x80 | size]) if size < 126 else bytes([0x80 | 126]) + struct.pack(">H", size) if size < 65536 \
            else bytes([0x80 | 127]) + struct.pack(">Q", size)
        self.socket.sendall(bytes([0x81]) + length + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def read(self, count: int) -> bytes:
        buffer = b""
        while len(buffer) < count:
            chunk = self.socket.recv(count - len(buffer))
            if not chunk:
                raise EOFError
            buffer += chunk
        return buffer

    def receive(self) -> str:
        message = b""
        while True:
            first, second = self.read(2)
            size = second & 0x7F
            if size == 126:
                size = struct.unpack(">H", self.read(2))[0]
            elif size == 127:
                size = struct.unpack(">Q", self.read(8))[0]
            payload = self.read(size)
            if first & 0x0F in (0x0, 0x1):
                message += payload
                if first & 0x80:
                    return message.decode()


LABEL = "window.__TAURI_INTERNALS__?.metadata?.currentWebview?.label"
# Pointer input at viewport points; a target is [x, y] or a selector, whose centre is used.
POINTER = """(start, end) => {
  const point = target => {
    if (Array.isArray(target)) return target;
    const element = document.querySelector(target);
    if (!element) throw new Error(`No element matches ${target}`);
    element.scrollIntoView({block: 'center', inline: 'center'});
    const box = element.getBoundingClientRect();
    return [box.x + box.width / 2, box.y + box.height / 2];
  };
  const fire = (names, [x, y], buttons) => {
    const element = document.elementFromPoint(x, y) ?? document.body;
    const init = {bubbles: true, cancelable: true, composed: true, view: window, clientX: x, clientY: y, button: 0, buttons,
                  detail: 1, pointerId: 1, pointerType: 'mouse', isPrimary: true};
    for (const name of names) element.dispatchEvent(new (name.startsWith('pointer') ? PointerEvent : MouseEvent)(name, init));
    return element;
  };
  const from = point(start), to = end ? point(end) : from;
  fire(['pointermove', 'mousemove'], from, 0);
  const pressed = fire(['pointerdown', 'mousedown'], from, 1);
  pressed.closest('input, textarea, select, button, a, [tabindex], [contenteditable]')?.focus();
  for (let step = 1; end && step <= 10; step++)
    fire(['pointermove', 'mousemove'], from.map((value, axis) => value + (to[axis] - value) * step / 10), 1);
  const released = fire(['pointerup', 'mouseup'], to, 0);
  if (released === pressed) fire(['click'], to, 0);
  return {from, to, pressed: pressed.id || pressed.tagName, released: released.id || released.tagName};
}"""
TYPE = """(text, selector) => {
  const element = selector ? document.querySelector(selector) : document.activeElement;
  if (!element) throw new Error(`No element matches ${selector}`);
  element.focus();
  if (!document.execCommand('insertText', false, text)) throw new Error('The focused element does not take text');
  return element.value ?? element.textContent;
}"""
KEY = """(combination) => {
  const modifiers = combination.split('+'), key = modifiers.pop(), held = name => modifiers.includes(name);
  const code = /^[a-z]$/i.test(key) ? `Key${key.toUpperCase()}` : /^[0-9]$/.test(key) ? `Digit${key}` : key;
  const init = {key, code, bubbles: true, cancelable: true, composed: true, view: window, ctrlKey: held('ctrl'),
                shiftKey: held('shift'), altKey: held('alt'), metaKey: held('meta')};
  const element = document.activeElement ?? document.body;
  const unhandled = element.dispatchEvent(new KeyboardEvent('keydown', init));
  element.dispatchEvent(new KeyboardEvent('keyup', init));
  return {target: element.id || element.tagName, defaultPrevented: !unhandled};
}"""


def inspector() -> str:
    """Address of the desktop app's WebKit inspector, which bin/desktop.sh run --inspect picks and records."""
    record = Path(__file__).resolve().parents[1] / "cache/desktop/inspector"
    address = os.environ.get("INFERENCE_INSPECTOR") or (record.read_text().strip() if record.exists() else "")
    if not address:
        raise SystemExit("No desktop inspector. Start the app with: bin/desktop.sh run --inspect")
    return address


class View:
    """An inspector session with one desktop WebView. Page commands travel inside Target.sendMessageToTarget."""

    def __init__(self, path: str) -> None:
        self.number, self.events, self.sent, self.target = path.split("/")[3], [], 0, None
        self.socket = WebSocket(f"ws://{inspector()}{path}")
        self.read(time.monotonic() + 1, until_target=True)
        if not self.target:
            self.socket.socket.close()
            raise EOFError
        try:
            self.label = self.evaluate(LABEL, timeout=3) or self.number
        except TimeoutError:
            # The renderer has exited: the view answers nothing and goes by its target number until the app reloads it.
            self.label = None

    def read(self, deadline: float, until_target: bool = False) -> dict | None:
        """The next message from the page, or None at the deadline."""
        while (left := deadline - time.monotonic()) > 0:
            self.socket.socket.settimeout(left)
            try:
                message = json.loads(self.socket.receive())
            except TimeoutError:
                break
            params = message.get("params", {})
            if "error" in message:
                raise SystemExit(json.dumps(message["error"]))
            if message.get("method") == "Target.targetCreated" and not params["targetInfo"].get("isProvisional"):
                self.target = params["targetInfo"]["targetId"]
            elif message.get("method") == "Target.didCommitProvisionalTarget":
                self.target = params["newTargetId"]  # A navigation moved the page to another process.
            elif message.get("method") == "Target.dispatchMessageFromTarget":
                return json.loads(params["message"])
            if until_target and self.target:
                break
        return None

    def call(self, method: str, params: dict | None = None, timeout: float = 30) -> dict:
        self.sent += 1
        message = json.dumps({"id": self.sent, "method": method, "params": params or {}})
        self.socket.send(json.dumps({"id": self.sent, "method": "Target.sendMessageToTarget",
                                     "params": {"targetId": self.target, "message": message}}))
        deadline = time.monotonic() + timeout
        while reply := self.read(deadline):
            if reply.get("id") == self.sent:
                if "error" in reply:
                    raise SystemExit(json.dumps(reply["error"]))
                return reply["result"]
            self.events.append(reply)
        raise TimeoutError(f"No reply to {method} within {timeout:g}s")

    def listen(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while event := self.read(deadline):
            self.events.append(event)

    def evaluate(self, expression: str, gesture: bool = False, timeout: float = 900) -> object:
        """The awaited value of an expression. gesture grants the user activation that media and clipboard calls need."""
        result = self.call("Runtime.evaluate", {"expression": expression, "emulateUserGesture": gesture}, timeout)
        if not result.get("wasThrown") and "objectId" in result["result"]:
            result = self.call("Runtime.callFunctionOn", {
                "objectId": result["result"]["objectId"], "functionDeclaration": "function() { return this; }",
                "returnByValue": True, "awaitPromise": True}, timeout)
        if result.get("wasThrown"):
            raise SystemExit(str(result["result"].get("description") or result["result"].get("value")))
        return result["result"].get("value")


def attach(path: str) -> View:
    # WebKit serves one frontend per view and closes the previous one late. A connection that races that close gets no
    # target or is dropped with it, and has to be made again.
    for _ in range(20):
        try:
            return View(path)
        except (EOFError, ConnectionError):
            time.sleep(0.3)
    raise SystemExit(f"View {path.split('/')[3]} is held by another inspector, such as an open Web Inspector window")


def views() -> list[View]:
    """Every WebView of the desktop app, each with its Tauri label."""
    # WebKit gives a view to one inspector, and a second connection ends the first, so commands take turns.
    global turn
    turn = open(__file__)
    fcntl.flock(turn, fcntl.LOCK_EX)
    try:
        listing = urllib.request.urlopen(f"http://{inspector()}/", timeout=10).read().decode()
    except urllib.error.URLError:
        raise SystemExit(f"No desktop inspector at {inspector()}. Start the app with: bin/desktop.sh run --inspect")
    return [attach(path) for path in sorted(set(re.findall(r"/socket/\d+/\d+/WebPage", listing)))]


def view(name: str) -> View:
    for session in views():
        if name.removeprefix("@") in (session.label, session.number):
            return session
    raise SystemExit(f"No desktop view {name}. tests/browser.py views lists them")


def console(session: View, seconds: float) -> None:
    session.call("Console.enable")  # The page replays the messages it kept, then reports new ones.
    session.listen(max(seconds, 0.3))
    for event in session.events:
        if event["method"] == "Console.messageAdded":
            message = event["params"]["message"]
            frames = message.get("stackTrace", {}).get("callFrames", [])
            print(json.dumps({
                "level": message["level"], "source": message["source"], "text": message["text"],
                "arguments": [item.get("preview", {}).get("properties") or item.get("value", item.get("description"))
                              for item in message.get("parameters", [])[1:]],
                "at": f"{message.get('url', '')}:{message.get('line', 0)}:{message.get('column', 0)}",
                "stack": [f"{frame['functionName']} {frame['url']}:{frame['lineNumber']}" for frame in frames[1:6]]}))


def network(session: View, seconds: float, action: str | None) -> None:
    """Report what the view loads for some seconds after an action: a reload, a script to evaluate, or nothing."""
    session.call("Network.enable")
    if action == "reload":
        session.call("Page.reload", {"ignoreCache": True})
    elif action:
        session.evaluate(sys.stdin.read() if action == "-" else open(action).read(), gesture=True)
    session.listen(seconds)
    requests = {}
    for event in session.events:
        kind, params = event["method"].removeprefix("Network."), event.get("params", {})
        row = requests.setdefault(params.get("requestId"), {})
        if kind == "requestWillBeSent":
            row.update(method=params["request"]["method"], url=params["request"]["url"], type=params.get("type"))
        elif kind == "webSocketCreated":
            row.update(method="GET", url=params["url"], type="WebSocket", frames=0)
        elif kind in ("responseReceived", "webSocketHandshakeResponseReceived"):
            row.update(status=params["response"]["status"])
        elif kind == "loadingFailed":
            row.update(error=params["errorText"], canceled=params.get("canceled", False))
        elif kind == "webSocketFrameError":
            row.update(error=params["errorMessage"])
        elif kind in ("webSocketFrameSent", "webSocketFrameReceived"):
            row["frames"] = row.get("frames", 0) + 1
        elif kind == "webSocketClosed":
            row.update(closed=True)
    for row in requests.values():
        if "url" in row:
            print(json.dumps(row))


def close_view(session: View) -> None:
    try:
        session.evaluate('window.__TAURI__.window.getCurrentWindow().close(); true')
    except EOFError:
        pass  # The requested close may end the inspector before its evaluation reply arrives.


def main(args: list[str]) -> None:
    match args:
        case ["desktop-memory"]:
            import desktop_measure
            desktop_measure.main()
        case ["desktop-check"]:
            import desktop
            desktop.main()
        case ["desktop-window-check"]:
            import runpy
            runpy.run_path(str(Path(__file__).with_name('desktop_window.py')),run_name='__main__')
        case ["close", label]:
            close_view(view(label))
            print("Close requested")
        case ["views"]:
            for session in views():
                state = session.evaluate("({url: location.href, title: document.title, visibility: document.visibilityState})") \
                    if session.label else {"unresponsive": True}
                print(json.dumps({"view": f"@{session.label or session.number}", "target": session.number, **state}))
        case ["console", tab, *seconds] if len(seconds) <= 1:
            console(view(tab), float(seconds[0]) if seconds else 0)
        case ["network", tab, seconds, *action] if len(action) <= 1:
            network(view(tab), float(seconds), action[0] if action else None)
        case ["click", tab, selector]:
            print(json.dumps(view(tab).evaluate(f"({POINTER})({json.dumps(selector)})", gesture=True)))
        case ["click", tab, x, y]:
            print(json.dumps(view(tab).evaluate(f"({POINTER})([{float(x)}, {float(y)}])", gesture=True)))
        case ["drag", tab, x1, y1, x2, y2]:
            points = f"[{float(x1)}, {float(y1)}], [{float(x2)}, {float(y2)}]"
            print(json.dumps(view(tab).evaluate(f"({POINTER})({points})", gesture=True)))
        case ["type", tab, text, *selector] if len(selector) <= 1:
            print(json.dumps(view(tab).evaluate(f"({TYPE})({json.dumps(text)}, {json.dumps((selector or [None])[0])})", gesture=True)))
        case ["key", tab, combination]:
            print(json.dumps(view(tab).evaluate(f"({KEY})({json.dumps(combination)})", gesture=True)))
        case ["inspect", tab, method, *rest]:
            session = view(tab)
            while method:
                params = json.loads(rest.pop(0)) if rest and rest[0].startswith("{") else {}
                print(json.dumps(session.call(method, params)))
                method = rest.pop(0) if rest else None
        case ["shot", tab, out] if tab.startswith("@"):
            session = view(tab)
            width, height = session.evaluate("[innerWidth, innerHeight]")
            image = session.call("Page.snapshotRect", {"x": 0, "y": 0, "width": width, "height": height,
                                                       "coordinateSystem": "Viewport"})["dataURL"]
            with open(out, "wb") as output:
                output.write(base64.b64decode(image.split(",", 1)[1]))
            print(f"{width}x{height} CSS pixels -> {out}")
        case ["eval", tab, source]:
            expression = sys.stdin.read() if source == "-" else Path(source).read_text()
            print(json.dumps(view(tab).evaluate(expression)))
        case _:
            raise SystemExit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except TimeoutError as error:
        raise SystemExit(str(error))
    except EOFError:
        raise SystemExit("The connection closed. A desktop view serves one inspector at a time")
