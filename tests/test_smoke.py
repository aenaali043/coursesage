"""Offline smoke tests: retrieval, tools, and the agent loop with a mock model.

Run:  python -m unittest discover -s tests -v      (no API key required)
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

import mock_llm  # noqa: E402
from coursesage.agent import CourseAgent  # noqa: E402
from coursesage.config import Settings  # noqa: E402
from coursesage.kb import CourseKB, parse_timestamp  # noqa: E402
from coursesage.tools import ToolBox  # noqa: E402


def mock_settings(port: int = 9999) -> Settings:
    return Settings(
        provider="openai",
        model="mock",
        base_url=f"http://127.0.0.1:{port}/v1",
        api_key="test-key",
        max_steps=4,
        tool_mode="auto",
    )


class KBTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = CourseKB()

    def test_kb_loaded(self):
        stats = self.kb.stats()
        self.assertGreater(stats["chapters"], 40)
        self.assertGreater(stats["chunks"], 300)

    def test_retrieval_finds_right_section(self):
        cases = {
            "slicing step negative": "Slicing",
            "lambda function": "Lambda",
            "what is RAG": "RAG",
            "hallucination": "Hallucination",
            "kwargs": "arguments",
            "operator precedence": "precedence",
        }
        for query, expected in cases.items():
            hits = self.kb.search(query, k=1)
            self.assertTrue(hits, f"no hits for {query}")
            self.assertIn(expected.lower(), hits[0].chunk["chapter"].lower(), f"query={query}")

    def test_timestamp_parser(self):
        self.assertEqual(parse_timestamp("01:32:57"), 5577)
        self.assertEqual(parse_timestamp("10:00"), 600)
        self.assertEqual(parse_timestamp("754"), 754)
        self.assertEqual(parse_timestamp(90), 90)

    def test_outline_tracks(self):
        self.assertTrue(all(r["track"] == "AI" for r in self.kb.outline("AI")))
        self.assertTrue(all(r["track"] == "Python" for r in self.kb.outline("python")))


class ToolTest(unittest.TestCase):
    def setUp(self):
        self.tools = ToolBox(CourseKB())

    def test_search_tool(self):
        out = self.tools.call("search_course", {"query": "dictionary methods", "top_k": 2})
        self.assertEqual(len(out["results"]), 2)
        self.assertIn("&t=", out["results"][0]["link"])

    def test_window_tool(self):
        out = self.tools.call("transcript_window", {"start": "01:32:57", "minutes": 2})
        self.assertTrue(out["text"])
        self.assertEqual(out["chapter"], "Slicing & step (stride)")

    def test_run_python(self):
        out = self.tools.call("run_python", {"code": "print('hello'[::-1])"})
        self.assertEqual(out["stdout"].strip(), "olleh")
        self.assertEqual(out["exit_code"], 0)

    def test_run_python_error_is_reported(self):
        out = self.tools.call("run_python", {"code": "1/0"})
        self.assertNotEqual(out["exit_code"], 0)
        self.assertIn("ZeroDivisionError", out["stderr"])

    def test_unknown_tool_is_safe(self):
        self.assertIn("error", self.tools.call("nope", {}))

    def test_note_roundtrip(self):
        self.tools.call("save_note", {"title": "Smoke test note", "content": "- item"})
        self.assertIn("Smoke test note", self.tools.call("recall_notes", {"query": "Smoke"})["notes"])


class AgentNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 9991
        cls.server = mock_llm.start(cls.port, "native")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_native_tool_call_roundtrip(self):
        agent = CourseAgent(settings=mock_settings(self.port))
        reply = agent.ask("Explain slicing in Python")
        self.assertEqual(reply.mode, "native")
        self.assertEqual(reply.tool_calls[0]["name"], "search_course")
        self.assertIn("youtube.com", reply.text)
        self.assertGreaterEqual(len(agent.messages), 4)

    def test_reset_clears_history(self):
        agent = CourseAgent(settings=mock_settings(self.port))
        agent.ask("hello")
        agent.reset()
        self.assertEqual(len(agent.messages), 1)


class AgentTextModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 9992
        cls.server = mock_llm.start(cls.port, "text")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_text_protocol_roundtrip(self):
        settings = mock_settings(self.port)
        settings.tool_mode = "text"
        agent = CourseAgent(settings=settings)
        reply = agent.ask("What is a lambda function?")
        self.assertEqual(reply.mode, "text")
        self.assertEqual(reply.tool_calls[0]["name"], "search_course")
        self.assertIn("youtube.com", reply.text)


class ParseTest(unittest.TestCase):
    def test_parse_variants(self):
        parse = CourseAgent._parse_text_tool
        name, args = parse('TOOL: search_course\nARGS: {"query": "slicing", "top_k": 3}')
        self.assertEqual(name, "search_course")
        self.assertEqual(args["query"], "slicing")

        name, args = parse('```json\n{"tool": "course_outline", "arguments": {}}\n```')
        self.assertEqual(name, "course_outline")

        self.assertIsNone(parse("Just a normal answer with no tools."))


if __name__ == "__main__":
    unittest.main(verbosity=2)
