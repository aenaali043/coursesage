"""A fake OpenAI-compatible server used to test the agent without API keys.

It behaves like a very simple model:
  * first turn  -> asks the agent to call search_course
  * after the tool result arrives -> writes a grounded answer with a timestamp link
  * --mode text -> does the same through the "TOOL:/ARGS:" text protocol

Run standalone:  python examples/mock_llm.py --port 9999 --mode native
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _tool_result(messages: list[dict]) -> dict | None:
    decoder = json.JSONDecoder()
    for msg in messages:
        if msg.get("role") == "tool":
            try:
                return json.loads(msg["content"])
            except (json.JSONDecodeError, TypeError):
                return None
    for msg in messages:
        content = str(msg.get("content") or "")
        if msg.get("role") == "user" and content.startswith("TOOL_RESULT "):
            try:
                data, _ = decoder.raw_decode(content[len("TOOL_RESULT "):].lstrip())
                return data
            except json.JSONDecodeError:
                return None
    return None


def _answer_from(result: dict) -> str:
    hits = result.get("results") or []
    if not hits:
        return "I could not find that in the course material."
    top = hits[0]
    return (
        f"According to the course at {top['start']} ({top['chapter']}), the key idea is:\n\n"
        f"> {top['text'][:160]}...\n\n"
        f"Watch it here: {top['link']}"
    )


def build_handler(mode: str = "native"):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            messages = payload.get("messages", [])
            result = _tool_result(messages)

            if result is None:
                query = next(
                    (m["content"] for m in reversed(messages) if m["role"] == "user"), "python"
                )
                query = str(query)[:200]
                if mode == "native":
                    message = {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "search_course",
                                    "arguments": json.dumps({"query": query, "top_k": 3}),
                                },
                            }
                        ],
                    }
                else:
                    message = {
                        "role": "assistant",
                        "content": f'TOOL: search_course\nARGS: {{"query": {json.dumps(query)}, "top_k": 3}}',
                    }
            else:
                message = {"role": "assistant", "content": _answer_from(result)}

            body = json.dumps(
                {
                    "id": "mock",
                    "object": "chat.completion",
                    "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def start(port: int = 9999, mode: str = "native") -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("127.0.0.1", port), build_handler(mode))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--mode", choices=["native", "text"], default="native")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), build_handler(args.mode))
    print(f"mock LLM on http://127.0.0.1:{args.port}/v1 ({args.mode} mode)")
    server.serve_forever()
