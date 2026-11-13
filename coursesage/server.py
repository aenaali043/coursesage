"""Minimal local web UI for CourseSage (standard library only)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .agent import CourseAgent
from .config import Settings
from .llm import LLMError

STATIC = Path(__file__).resolve().parent / "static"


def _display_call(call: dict) -> dict:
    """Normalise a tool call for the UI (arguments may arrive as a JSON string)."""
    args = call.get("args")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"raw": args}
    return {"name": call["name"], "args": args or {}}


def make_handler(agent: CourseAgent, lock: threading.Lock):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CourseSage/1.0"

        def log_message(self, fmt, *args):  # quieter console
            if agent.settings.verbose:
                print(f"[http] {fmt % args}")

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict) -> None:
            self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html"}:
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/avatar.png":
                self._send(200, (STATIC / "avatar.png").read_bytes(), "image/png")
            elif self.path == "/api/outline":
                self._json(200, {"chapters": agent.kb.outline()})
            elif self.path == "/api/health":
                s = agent.settings
                self._json(200, {
                    "ok": True,
                    "provider": s.provider,
                    "model": s.model,
                    "base_url": s.base_url,
                    "kb": agent.kb.stats(),
                })
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid JSON body"})
                return

            if self.path == "/api/reset":
                with lock:
                    agent.reset()
                self._json(200, {"ok": True})
                return

            if self.path != "/api/chat":
                self._json(404, {"error": "not found"})
                return

            message = (payload.get("message") or "").strip()
            if not message:
                self._json(400, {"error": "message is required"})
                return

            trace: list[dict] = []
            agent.on_event = lambda kind, data: trace.append({"kind": kind, **data}) if kind == "tool" else None
            try:
                with lock:
                    reply = agent.ask(message)
            except LLMError as exc:
                self._json(502, {"error": str(exc)})
                return
            self._json(
                200,
                {
                    "answer": reply.text,
                    "steps": reply.steps,
                    "mode": reply.mode,
                    "tools": [_display_call(t) for t in reply.tool_calls],
                },
            )

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    settings = Settings.from_env()
    try:
        agent = CourseAgent(settings=settings)
    except LLMError as exc:
        print(f"cannot start: {exc}")
        print("Copy .env.example to .env and add your API key, then run again.")
        return
    lock = threading.Lock()
    httpd = ThreadingHTTPServer((host, port), make_handler(agent, lock))

    def _warm_up() -> None:  # wake the hosted model so the first question is fast
        try:
            agent.client.chat([{"role": "user", "content": "ping"}], temperature=0)
        except Exception:
            pass

    threading.Thread(target=_warm_up, daemon=True).start()
    print(f"CourseSage web UI -> http://{host}:{port}  ({settings.describe()})")
    print("Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
