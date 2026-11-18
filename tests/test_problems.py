"""Offline tests for the practice-problem bank and the auto-grader.

Run:  python -m unittest discover -s tests -v      (no API key required)
"""

from __future__ import annotations

import os
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coursesage.grader import grade  # noqa: E402
from coursesage.kb import CourseKB  # noqa: E402
from coursesage.problems import (  # noqa: E402
    PROBLEMS,
    chapter_reference,
    format_problem_list,
    get_problem,
    list_problems,
)


class ProblemBankTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = CourseKB()

    def test_bank_has_three_difficulties(self):
        levels = {p.difficulty for p in PROBLEMS}
        self.assertEqual(levels, {"easy", "medium", "hard"})
        self.assertGreaterEqual(len(PROBLEMS), 12)

    def test_ids_are_unique(self):
        ids = [p.id for p in PROBLEMS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_problem_cites_a_real_chapter(self):
        titles = {c["title"] for c in self.kb.chapters}
        for problem in PROBLEMS:
            self.assertIn(problem.chapter, titles, f"{problem.id} has no matching chapter")

    def test_chapter_reference_resolves_to_a_timestamp(self):
        problem = get_problem("two-sum")
        ref = chapter_reference(self.kb, problem)
        self.assertIsNotNone(ref["start"])
        self.assertTrue(ref["link"].startswith("https://"))

    def test_every_problem_has_tests_and_hints(self):
        for problem in PROBLEMS:
            self.assertGreaterEqual(len(problem.tests), 3, problem.id)
            self.assertGreaterEqual(len(problem.hints), 1, problem.id)
            self.assertTrue(problem.examples, problem.id)

    def test_filters(self):
        self.assertTrue(all(p.difficulty == "hard" for p in list_problems(difficulty="hard")))
        self.assertTrue(all("dict" in p.concept.lower() or "dictionar" in p.concept.lower()
                            for p in list_problems(topic="dictionar")))
        self.assertLessEqual(len(list_problems(limit=2)), 2)

    def test_list_rendering_mentions_the_command(self):
        text = format_problem_list(self.kb, list_problems(limit=2))
        self.assertIn("/grade", text)
        self.assertIn("course", text)


REFERENCE_SOLUTIONS = {
    "sum-even": "def sum_even(nums):\n    return sum(n for n in nums if n % 2 == 0)\n",
    "count-vowels": "def count_vowels(text):\n    return sum(1 for c in text.lower() if c in 'aeiou')\n",
    "second-largest": (
        "def second_largest(nums):\n"
        "    best = second = None\n"
        "    for n in nums:\n"
        "        if best is None or n > best:\n"
        "            second, best = best, n\n"
        "        elif n != best and (second is None or n > second):\n"
        "            second = n\n"
        "    return second\n"
    ),
    "reverse-words": "def reverse_words(sentence):\n    return ' '.join(sentence.split()[::-1])\n",
    "invert-dict": "def invert_dict(data):\n    return {str(v): k for k, v in data.items()}\n",
    "two-sum": (
        "def two_sum(nums, target):\n"
        "    seen = {}\n"
        "    for i, x in enumerate(nums):\n"
        "        if target - x in seen:\n"
        "            return [seen[target - x], i]\n"
        "        seen[x] = i\n"
        "    return []\n"
    ),
    "group-anagrams": (
        "def group_anagrams(words):\n"
        "    groups = {}\n"
        "    for w in words:\n"
        "        groups.setdefault(''.join(sorted(w)), []).append(w)\n"
        "    out = [sorted(v) for v in groups.values()]\n"
        "    out.sort(key=lambda g: g[0])\n"
        "    return out\n"
    ),
    "flatten": (
        "def flatten(nested):\n"
        "    result = []\n"
        "    for item in nested:\n"
        "        if isinstance(item, list):\n"
        "            result.extend(flatten(item))\n"
        "        else:\n"
        "            result.append(item)\n"
        "    return result\n"
    ),
    "top-words": (
        "def top_words(text, k):\n"
        "    counts = {}\n"
        "    for w in text.split():\n"
        "        counts[w] = counts.get(w, 0) + 1\n"
        "    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))\n"
        "    return [[w, c] for w, c in items[:k]]\n"
    ),
    "palindrome": (
        "def is_palindrome(text):\n"
        "    cleaned = ''.join(c.lower() for c in text if c.isalnum())\n"
        "    return cleaned == cleaned[::-1]\n"
    ),
    "fizzbuzz-list": (
        "def fizzbuzz_list(n):\n"
        "    out = []\n"
        "    for i in range(1, n + 1):\n"
        "        if i % 15 == 0:\n"
        "            out.append('FizzBuzz')\n"
        "        elif i % 3 == 0:\n"
        "            out.append('Fizz')\n"
        "        elif i % 5 == 0:\n"
        "            out.append('Buzz')\n"
        "        else:\n"
        "            out.append(str(i))\n"
        "    return out\n"
    ),
    "rotate-list": (
        "def rotate_list(nums, k):\n"
        "    if not nums:\n"
        "        return []\n"
        "    k = k % len(nums)\n"
        "    if k == 0:\n"
        "        return list(nums)\n"
        "    return nums[-k:] + nums[:-k]\n"
    ),
    "merge-intervals": (
        "def merge_intervals(intervals):\n"
        "    if not intervals:\n"
        "        return []\n"
        "    items = sorted(intervals, key=lambda iv: iv[0])\n"
        "    merged = [list(items[0])]\n"
        "    for start, end in items[1:]:\n"
        "        if start <= merged[-1][1]:\n"
        "            merged[-1][1] = max(merged[-1][1], end)\n"
        "        else:\n"
        "            merged.append([start, end])\n"
        "    return merged\n"
    ),
    "transpose": (
        "def transpose(matrix):\n"
        "    if not matrix:\n"
        "        return []\n"
        "    return [[matrix[r][c] for r in range(len(matrix))] for c in range(len(matrix[0]))]\n"
    ),
}


class ReferenceSolutionTest(unittest.TestCase):
    """Every problem must be solvable: the reference answer passes all hidden tests."""

    def test_reference_solutions_pass_every_problem(self):
        for problem in PROBLEMS:
            code = REFERENCE_SOLUTIONS.get(problem.id)
            self.assertIsNotNone(code, f"no reference solution for {problem.id}")
            result = grade(problem, code)
            self.assertEqual(result["verdict"], "PASS", f"{problem.id}: {result}")


class GraderTest(unittest.TestCase):
    def test_correct_solution_passes_every_test(self):
        problem = get_problem("sum-even")
        code = "def sum_even(nums):\n    return sum(n for n in nums if n % 2 == 0)\n"
        result = grade(problem, code)
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertEqual(result["passed"], result["total"])

    def test_wrong_solution_fails_and_shows_the_test(self):
        problem = get_problem("sum-even")
        code = "def sum_even(nums):\n    return 999\n"
        result = grade(problem, code)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["passed"], 0)
        self.assertTrue(any(r["status"] == "fail" for r in result["results"]))

    def test_missing_function_is_reported(self):
        problem = get_problem("sum-even")
        result = grade(problem, "x = 1\n")
        self.assertEqual(result["verdict"], "ERROR")
        self.assertIn("sum_even", result["error"])

    def test_broken_code_is_reported(self):
        problem = get_problem("sum-even")
        result = grade(problem, "def sum_even(nums)\n    return 1\n")
        self.assertEqual(result["verdict"], "ERROR")

    def test_empty_submission_is_rejected(self):
        result = grade(get_problem("sum-even"), "   ")
        self.assertIn("no code", result["error"].lower())

    def test_grade_is_deterministic_for_every_problem(self):
        for problem in PROBLEMS:
            result = grade(problem, f"def {problem.func}({problem.args}):\n    return None\n")
            self.assertIn(result["verdict"], {"FAIL", "PASS", "PARTIAL", "ERROR"})

    def test_allow_code_exec_switch_disables_grading(self):
        problem = get_problem("sum-even")
        code = "def sum_even(nums):\n    return 0\n"
        with unittest.mock.patch.dict(os.environ, {"ALLOW_CODE_EXEC": "0"}):
            result = grade(problem, code)
        self.assertEqual(result["verdict"], "DISABLED")
        self.assertIn("ALLOW_CODE_EXEC", result["error"])


class AgentCommandTest(unittest.TestCase):
    def test_problems_command_is_answered_without_a_model(self):
        from coursesage.agent import CourseAgent
        from coursesage.config import Settings

        agent = CourseAgent(settings=Settings(provider="openai", model="mock",
                                              base_url="http://127.0.0.1:9/v1", api_key="k"))
        reply = agent.ask("/problems dictionaries 2")
        self.assertEqual(reply.mode, "local")
        self.assertIn("/grade", reply.text)

    def test_grade_command_runs_the_submission(self):
        from coursesage.agent import CourseAgent
        from coursesage.config import Settings

        agent = CourseAgent(settings=Settings(provider="openai", model="mock",
                                              base_url="http://127.0.0.1:9/v1", api_key="k"))
        reply = agent.ask(
            "/grade sum-even\n```\ndef sum_even(nums):\n    return sum(n for n in nums if n % 2 == 0)\n```"
        )
        self.assertEqual(reply.mode, "local")
        self.assertIn("PASS", reply.text)

    def test_unknown_problem_is_reported(self):
        from coursesage.agent import CourseAgent
        from coursesage.config import Settings

        agent = CourseAgent(settings=Settings(provider="openai", model="mock",
                                              base_url="http://127.0.0.1:9/v1", api_key="k"))
        reply = agent.ask("/grade not-a-problem\n```\nx = 1\n```")
        self.assertIn("Unknown problem", reply.text)


if __name__ == "__main__":
    unittest.main()
