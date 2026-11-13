#!/usr/bin/env python3
"""CourseSage entry point.

  python run.py              # interactive chat in the terminal
  python run.py serve        # local web UI at http://127.0.0.1:8000
  python run.py outline      # print the chapter map
  python run.py search "slicing step"   # raw retrieval, no LLM needed
  python run.py doctor       # check config + knowledge base
"""

from __future__ import annotations

import sys

from coursesage.cli import main as chat_main
from coursesage.config import Settings
from coursesage.kb import CourseKB


def main() -> int:
    args = sys.argv[1:]
    command = args[0] if args else "chat"

    if command in {"chat", ""}:
        return chat_main(args[1:])

    if command == "serve":
        from coursesage.server import serve

        port = int(args[1]) if len(args) > 1 and args[1].isdigit() else 8000
        serve(port=port)
        return 0

    if command == "outline":
        kb = CourseKB()
        track = args[1] if len(args) > 1 else None
        for row in kb.outline(track):
            print(f"{row['start']}  [{row['track']:6}]  {row['chapter']}")
        return 0

    if command == "search":
        query = " ".join(args[1:])
        if not query:
            print("usage: python run.py search <query>")
            return 2
        kb = CourseKB()
        for hit in kb.search(query, k=5):
            print(f"\n[{hit.chunk['start']}] {hit.chunk['chapter']}  (score {hit.score:.2f})")
            print(f"  {hit.chunk['text'][:500]}...")
        return 0

    if command == "doctor":
        settings = Settings.from_env()
        kb = CourseKB()
        stats = kb.stats()
        print("CourseSage doctor")
        print(f"  provider : {settings.provider}")
        print(f"  model    : {settings.model}")
        print(f"  base_url : {settings.base_url}")
        print(f"  api key  : {'set' if settings.api_key else 'MISSING'}")
        print(f"  tool mode: {settings.tool_mode}")
        print(f"  knowledge: {stats['chapters']} chapters / {stats['chunks']} passages / {stats['duration']}")
        probe = kb.search("lambda function", k=1)
        print(f"  retrieval: {'ok' if probe else 'FAILED'} "
              f"({'first hit ' + probe[0].chunk['start'] if probe else 'no hits'})")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
