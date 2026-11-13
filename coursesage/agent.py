"""The agent loop: reason -> call tool -> observe -> answer."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from .config import Settings
from .kb import CourseKB
from .llm import LLMClient, LLMError
from .prompts import SYSTEM_PROMPT, TEXT_TOOL_PROTOCOL
from .tools import ToolBox, dumps

Event = Callable[[str, dict], None]

TOOL_HEAD_RE = re.compile(r"TOOL:\s*([a-zA-Z_][\w]*)\s*(?:[\r\n]+)?\s*ARGS:\s*", re.S)
TOOL_JSON_RE = re.compile(r'```(?:json)?\s*(\{"(?:tool|name)".*?\})\s*```', re.S)


@dataclass
class AgentReply:
    text: str
    steps: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    mode: str = "native"


class CourseAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        kb: CourseKB | None = None,
        client: LLMClient | None = None,
        toolbox: ToolBox | None = None,
        on_event: Event | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.kb = kb or CourseKB()
        self.toolbox = toolbox or ToolBox(self.kb)
        self.client = client or LLMClient(self.settings)
        self.on_event = on_event
        self.mode = "text" if self.settings.tool_mode == "text" else "native"
        self.messages: list[dict] = [{"role": "system", "content": self._system_prompt()}]

    # ------------------------------------------------------------------ helpers
    def _system_prompt(self) -> str:
        prompt = SYSTEM_PROMPT
        if self.mode == "text":
            docs = "\n".join(
                f"- {s['function']['name']}: {s['function']['description']} args={json.dumps(s['function']['parameters'].get('properties', {}))}"
                for s in self.toolbox.specs()
            )
            prompt += TEXT_TOOL_PROTOCOL.format(tool_docs=docs)
        return prompt

    def _emit(self, kind: str, payload: dict) -> None:
        if self.on_event:
            self.on_event(kind, payload)

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": self._system_prompt()}]

    def switch_mode(self, mode: str) -> None:
        self.mode = mode
        self.messages[0] = {"role": "system", "content": self._system_prompt()}

    # --------------------------------------------------------------------- ask
    def ask(self, user_message: str) -> AgentReply:
        self.messages.append({"role": "user", "content": user_message})
        used: list[dict] = []
        repeat: dict[str, int] = {}
        steps = 0

        for step in range(1, self.settings.max_steps + 1):
            steps = step
            try:
                reply = self._chat()
            except LLMError as exc:
                if self.mode == "native" and "tool" in str(exc).lower():
                    self._emit("status", {"message": "Native tool calling unsupported, switching to text mode"})
                    self.switch_mode("text")
                    continue
                raise

            content = (reply.get("content") or "").strip()
            native_calls = reply.get("tool_calls") or []

            if native_calls:
                self.messages.append(
                    {"role": "assistant", "content": reply.get("content") or "", "tool_calls": native_calls}
                )
                for call in native_calls:
                    name = call["function"]["name"]
                    raw_args = call["function"].get("arguments") or "{}"
                    result = self._exec_once(name, raw_args, repeat, used)
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", f"call_{step}"),
                            "name": name,
                            "content": dumps(result),
                        }
                    )
                continue

            text_call = self._parse_text_tool(content)
            if text_call:
                name, args = text_call
                result = self._exec_once(name, args, repeat, used)
                self.messages.append({"role": "assistant", "content": content})
                self.messages.append({"role": "user", "content": "TOOL_RESULT " + dumps(result)})
                continue

            if not content:
                content = "I could not produce an answer for that. Please rephrase the question."

            self.messages.append({"role": "assistant", "content": content})
            self._emit("final", {"text": content, "steps": steps})
            return AgentReply(text=content, steps=steps, tool_calls=used, mode=self.mode)

        # Ran out of steps: force a final answer from what we have.
        self._emit("status", {"message": "Step budget exhausted, producing final answer"})
        self.messages.append(
            {"role": "user", "content": "Stop using tools now and answer with what you already have."}
        )
        try:
            reply = self._chat(with_tools=False)
            text = (reply.get("content") or "").strip() or "Step limit reached before I could answer."
        except LLMError as exc:
            text = f"Step limit reached and the model call failed: {exc}"
        self.messages.append({"role": "assistant", "content": text})
        return AgentReply(text=text, steps=steps, tool_calls=used, mode=self.mode)

    # ------------------------------------------------------------------ internals
    def _chat(self, with_tools: bool = True) -> dict:
        tools = self.toolbox.specs() if (with_tools and self.mode == "native") else None
        started = time.time()
        reply = self.client.chat(self.messages, tools=tools)
        self._emit("llm", {"ms": int((time.time() - started) * 1000)})
        return reply

    def _exec_once(self, name: str, args: str | dict, repeat: dict, used: list) -> dict:
        """Run a tool, but refuse to run the exact same call more than twice."""
        signature = name + "|" + (args if isinstance(args, str) else json.dumps(args, sort_keys=True))
        repeat[signature] = repeat.get(signature, 0) + 1
        if repeat[signature] > 2:
            return {
                "error": "Duplicate call skipped: you already have this result. "
                "Use the earlier TOOL_RESULT to answer, or call a different tool."
            }
        result = self._run_tool(name, args)
        used.append({"name": name, "args": args, "result": result})
        return result

    def _run_tool(self, name: str, raw_args: str | dict) -> dict:
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except json.JSONDecodeError:
                args = {}
                for match in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', raw_args):
                    args[match.group(1)] = match.group(2)
        else:
            args = raw_args

        started = time.time()
        result = self.toolbox.call(name, args)
        self._emit(
            "tool",
            {"name": name, "args": args, "ms": int((time.time() - started) * 1000), "result": result},
        )
        return result

    @staticmethod
    def _parse_text_tool(content: str) -> tuple[str, dict] | None:
        if not content:
            return None
        match = TOOL_HEAD_RE.search(content)
        if match:
            name = match.group(1)
            rest = content[match.end():].lstrip()
            rest = rest.removeprefix("```json").removeprefix("```").lstrip()
            try:
                args, _ = json.JSONDecoder().raw_decode(rest)
                if isinstance(args, dict):
                    return name, args
            except json.JSONDecodeError:
                pass
        for match in TOOL_JSON_RE.finditer(content):
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            name = payload.get("tool") or payload.get("name")
            args = payload.get("arguments") or payload.get("args") or {}
            if name:
                return name, args
        return None
