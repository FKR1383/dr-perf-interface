"""A local OpenAI-compatible chat-completions endpoint that replays a fixed script.

Exists so a real Kimi provider (and therefore the real per-step request path) can be
driven with no network and no model. Started in-process by run_agent_kimi.py.
"""
import json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Script:
    """Turn number -> the assistant message to stream back."""

    def __init__(self, turns):
        self.turns = turns          # list of dicts: {"text": str, "tool_call": {...} | None}
        self.i = 0
        self.lock = threading.Lock()

    def next(self):
        with self.lock:
            turn = self.turns[min(self.i, len(self.turns) - 1)]
            self.i += 1
            return turn


def make_handler(script):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _sse(self, obj):
            return ("data: " + json.dumps(obj) + "\n\n").encode()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            cap = os.environ.get("KIMI_CAPTURE_REQUESTS")
            if cap:
                with open(cap, "a") as fh:
                    fh.write(raw.decode("utf-8", "replace").rstrip("\n") + "\n")
            turn = script.next()
            created = int(time.time())
            base = {"id": "chatcmpl-stub", "object": "chat.completion.chunk",
                    "created": created, "model": "stub"}

            chunks = []
            chunks.append(dict(base, choices=[{"index": 0, "delta": {"role": "assistant"},
                                               "finish_reason": None}]))
            if turn.get("text"):
                chunks.append(dict(base, choices=[{"index": 0,
                                                   "delta": {"content": turn["text"]},
                                                   "finish_reason": None}]))
            tc = turn.get("tool_call")
            if tc:
                chunks.append(dict(base, choices=[{"index": 0, "delta": {"tool_calls": [{
                    "index": 0, "id": tc["id"], "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]}}]},
                    "finish_reason": None}]))
            chunks.append(dict(base, choices=[{"index": 0, "delta": {},
                                               "finish_reason": "tool_calls" if tc else "stop"}]))
            chunks.append(dict(base, choices=[],
                               usage={"prompt_tokens": 100, "completion_tokens": 20,
                                      "total_tokens": 120}))

            body = b"".join(self._sse(c) for c in chunks) + b"data: [DONE]\n\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            body = json.dumps({"data": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def start(turns):
    """Start the stub on a free port; returns (base_url, shutdown)."""
    script = Script(turns)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(script))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return f"http://127.0.0.1:{port}/v1", server.shutdown
