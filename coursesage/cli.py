"""Interactive terminal chat for CourseSage."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from .agent import CourseAgent
from .config import Settings
from .llm import LLMError
from .prompts import PLAN_TEMPLATE, QUIZ_TEMPLATE

BANNER = r"""
  ____                      ____
 / ___|___  _   _ _ __ ___ / ___|  __ _  __ _  ___
| |   / _ \| | | | '__/ __| |  _  / _` |/ _` |/ _ \
| |__| (_) | |_| | |  \__ \ |_| || (_| | (_| |  __/
 \____\___/ \__,_|_|  |___/\____| \__,_|\__, |\___|
                                        |___/
  CourseSage - study agent for "Best Python + AI Full Course"
  built by Aena Ali
"""

HELP = """commands
  /outline [Python|AI]  chapter list with timestamps
  /search <query>       raw transcript search
  /quiz <topic> [n]     generate a quiz
  /plan <topic> [days]  generate a study plan
  /notes                show saved notes
  /steps <n>            set the tool-call budget (default 6)
  /verbose              toggle tool tracing
  /reset                clear the conversation
  /help, /exit
"""


def _trace(settings: Settings):
    def on_event(kind: str, payload: dict) -> None:
        if kind == "tool":
            args = payload.get("args", {})
            short = ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())
            print(f"   \033[36m-> {payload['name']}({short}) {payload['ms']}ms\033[0m")
        elif kind == "status" and settings.verbose:
            print(f"   \033[90m.. {payload.get('message')}\033[0m")

    return on_event


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    settings = Settings.from_env()
    print(BANNER)
    print(f"model: {settings.describe()}  | mode: {settings.tool_mode}\n")

    try:
        agent = CourseAgent(settings=settings, on_event=_trace(settings))
    except LLMError as exc:
        print(f"\033[31m{exc}\033[0m")
        print("Tip: copy .env.example to .env and add your API key.")
        return 1

    stats = agent.kb.stats()
    print(f"knowledge base: {stats['chapters']} chapters, {stats['chunks']} passages, "
          f"{stats['duration']} of video\n")
    print("Ask a Python question, paste code that confuses you, or type /help.\n")

    first = " ".join(argv).strip()
    if first:
        _answer(agent, first)

    while True:
        try:
            line = input("\033[1m you >\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not line:
            continue
        if line in {"/exit", "/quit", "exit", "quit"}:
            print("bye")
            return 0
        if line == "/help":
            print(HELP)
            continue
        if line == "/reset":
            agent.reset()
            print("conversation cleared")
            continue
        if line == "/verbose":
            settings.verbose = not settings.verbose
            agent.on_event = _trace(settings)
            print(f"verbose={'on' if settings.verbose else 'off'}")
            continue
        if line.startswith("/steps"):
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                settings.max_steps = int(parts[1])
            print(f"max steps = {settings.max_steps}")
            continue
        if line.startswith("/outline"):
            track = line.split()[1] if len(line.split()) > 1 else None
            for row in agent.kb.outline(track):
                print(f"  {row['start']}  [{row['track']:6}] {row['chapter']}")
            print()
            continue
        if line.startswith("/search"):
            query = line[len("/search"):].strip()
            hits = agent.kb.search(query, k=5)
            if not hits:
                print("  no matches\n")
            for hit in hits:
                print(f"  [{hit.chunk['start']}] {hit.chunk['chapter']} (score {hit.score:.1f})")
                print(f"    {hit.chunk['text'][:220]}...")
            print()
            continue
        if line.startswith("/notes"):
            print(agent.toolbox.call("recall_notes", {})["notes"], "\n")
            continue
        if line.startswith("/quiz"):
            rest = line[len("/quiz"):].strip().split()
            count = "5"
            topic_words: list[str] = []
            for token in rest:
                if token.isdigit():
                    count = token
                else:
                    topic_words.append(token)
            topic = " ".join(topic_words) or "Python data types and operators"
            _answer(agent, QUIZ_TEMPLATE.format(topic=topic, count=count))
            continue
        if line.startswith("/plan"):
            rest = line[len("/plan"):].strip().split()
            days = "7"
            topic_words = []
            for token in rest:
                if token.isdigit():
                    days = token
                else:
                    topic_words.append(token)
            topic = " ".join(topic_words) or "the whole Python + AI course"
            _answer(agent, PLAN_TEMPLATE.format(topic=topic, days=days))
            continue

        _answer(agent, line)


def _answer(agent: CourseAgent, message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    try:
        reply = agent.ask(message)
    except LLMError as exc:
        print(f"\033[31mmodel error: {exc}\033[0m\n")
        return
    except KeyboardInterrupt:
        print("\n(interrupted)\n")
        return
    print(f"\033[32magent\033[0m [{stamp}] {reply.text}\n")
    print(f"\033[90m({reply.steps} step(s), mode={reply.mode})\033[0m\n")
