"""Tools the agent can call. Each tool returns plain JSON-serialisable data."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR
from .kb import CourseKB, parse_timestamp

NOTES_PATH = DATA_DIR / "notes.md"


class ToolBox:
    def __init__(self, kb: CourseKB, allow_code_execution: bool | None = None):
        self.kb = kb
        if allow_code_execution is None:
            flag = os.environ.get("ALLOW_CODE_EXEC", "1").strip().lower()
            allow_code_execution = flag not in {"0", "false", "no", "off"}
        self.allow_code_execution = allow_code_execution

    # --------------------------------------------------------------- registry
    def specs(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_course",
                    "description": (
                        "Semantic+keyword search inside the course transcript (Python section "
                        "00:00-10:48, AI vocabulary section 10:49-13:02). Use this for any "
                        "question about what the instructor explained, definitions, examples "
                        "or code behaviour."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What to look for, in plain words."},
                            "top_k": {"type": "integer", "description": "How many passages (1-8).", "default": 5},
                            "track": {
                                "type": "string",
                                "enum": ["Python", "AI"],
                                "description": "Optional filter: only Python or only AI material.",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "course_outline",
                    "description": "Return the chapter list with timestamps, so you can point the learner to the right part of the video.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "track": {
                                "type": "string",
                                "enum": ["Python", "AI"],
                                "description": "Optional filter for one track.",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "transcript_window",
                    "description": "Fetch what was said around a specific timestamp. Use after the learner mentions a time or when a search hit needs more surrounding context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "Timestamp like '01:32:57' or seconds like '5577'."},
                            "minutes": {"type": "integer", "description": "Window length in minutes (1-10).", "default": 3},
                        },
                        "required": ["start"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python",
                    "description": "Execute a short Python snippet and return stdout/stderr. Use to verify what code does before explaining it, or to check a learner's code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python source to run (short, no network, no file writes outside temp)."}
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_note",
                    "description": "Save a durable study note (summary, mistake to remember, generated quiz). Notes persist between sessions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string", "description": "Markdown content."},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recall_notes",
                    "description": "Read saved study notes, optionally filtered by a keyword.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "Optional keyword filter."}},
                    },
                },
            },
        ]

    def call(self, name: str, args: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool '{name}'", "available": [s["function"]["name"] for s in self.specs()]}
        try:
            return handler(**args)
        except TypeError as exc:
            return {"error": f"Bad arguments for {name}: {exc}"}
        except Exception as exc:  # noqa: BLE001 - tool errors must never kill the agent
            return {"error": f"{type(exc).__name__}: {exc}"}

    # ------------------------------------------------------------------- tools
    def _tool_search_course(self, query: str, top_k: int = 5, track: str | None = None) -> dict:
        top_k = max(1, min(int(top_k or 5), 8))
        hits = self.kb.search(query, k=top_k, track=track)
        if not hits:
            return {"query": query, "results": [], "note": "No passage matched. Try different wording or drop the track filter."}
        return {"query": query, "results": [h.to_dict() for h in hits]}

    def _tool_course_outline(self, track: str | None = None) -> dict:
        rows = self.kb.outline(track)
        return {"count": len(rows), "chapters": rows}

    def _tool_transcript_window(self, start: str, minutes: int = 3) -> dict:
        sec = parse_timestamp(start)
        minutes = max(1, min(int(minutes or 3), 10))
        return self.kb.window_at(sec, minutes)

    def _tool_run_python(self, code: str) -> dict:
        if not self.allow_code_execution:
            return {"error": "Code execution is disabled (ALLOW_CODE_EXEC=0)."}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snippet.py"
            path.write_text(code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tmp,
                )
                return {
                    "stdout": proc.stdout[-4000:],
                    "stderr": proc.stderr[-4000:],
                    "exit_code": proc.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"error": "Timed out after 10s. Infinite loop? Try a smaller example."}

    def _tool_save_note(self, title: str, content: str) -> dict:
        NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with NOTES_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {title}\n_{stamp}_\n\n{content.strip()}\n")
        return {"saved": True, "path": str(NOTES_PATH), "title": title}

    def _tool_recall_notes(self, query: str | None = None) -> dict:
        if not NOTES_PATH.exists():
            return {"notes": "No notes saved yet."}
        text = NOTES_PATH.read_text(encoding="utf-8")
        if query:
            blocks = [b for b in text.split("\n## ") if query.lower() in b.lower()]
            text = "\n## ".join(blocks) if blocks else f"No note matching '{query}'."
        return {"notes": text[-6000:]}


def dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=None, separators=(",", ":"))
