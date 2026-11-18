"""Run a learner's solution against a problem's hidden test cases.

The submission runs in a separate, isolated interpreter (no user site packages,
no API keys in the environment) with a hard timeout, so a wrong or infinite
loop cannot hang the app.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .problems import Problem

RUNNER = r'''
import ast, contextlib, io, json


def close(got, expected):
    if isinstance(got, bool) or isinstance(expected, bool):
        return got == expected
    if isinstance(got, (int, float)) and isinstance(expected, (int, float)):
        return abs(got - expected) < 1e-9
    if isinstance(got, (list, tuple)) and isinstance(expected, (list, tuple)):
        return len(got) == len(expected) and all(close(a, b) for a, b in zip(got, expected))
    if isinstance(got, dict) and isinstance(expected, dict):
        return set(got) == set(expected) and all(close(got[k], expected[k]) for k in got)
    return got == expected


def main():
    payload = json.load(open("cases.json", encoding="utf-8"))
    result = {}

    namespace = {"__name__": "solution"}
    try:
        source = open("solution.py", encoding="utf-8").read()
    except OSError as exc:
        result = {"error": "could not read the submission: %s" % exc}
    else:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, "solution.py", "exec"), namespace)
        except Exception as exc:
            result = {"error": "your code did not run: %s: %s" % (type(exc).__name__, exc)}

    if not result:
        fn = namespace.get(payload["func"])
        if not callable(fn):
            result = {"error": "define a function called %s(%s)" % (payload["func"], payload["args"])}
        else:
            results = []
            for index, case in enumerate(payload["cases"], 1):
                try:
                    args = ast.literal_eval(case["args"])
                    expected = ast.literal_eval(case["expected"])
                except Exception as exc:
                    results.append({"test": index, "status": "bad_case", "detail": str(exc)})
                    continue
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        got = fn(*args)
                    ok = close(got, expected)
                    results.append({
                        "test": index,
                        "status": "pass" if ok else "fail",
                        "input": case["args"],
                        "expected": case["expected"],
                        "got": repr(got)[:200],
                    })
                except Exception as exc:
                    results.append({
                        "test": index,
                        "status": "error",
                        "input": case["args"],
                        "detail": ("%s: %s" % (type(exc).__name__, exc))[:200],
                    })
            passed = sum(1 for r in results if r["status"] == "pass")
            result = {"passed": passed, "total": len(results), "results": results}

    with open("result.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh)


main()
'''


def _clean_env() -> dict:
    """Keep the environment but drop anything that looks like a credential."""
    drop = ("GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY", "ANTHROPIC_API_KEY")
    return {k: v for k, v in os.environ.items() if k not in drop and not k.endswith("_API_KEY")}


def code_execution_allowed() -> bool:
    """Honour the same ALLOW_CODE_EXEC switch as the run_python tool."""
    flag = os.environ.get("ALLOW_CODE_EXEC", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def grade(problem: Problem, code: str, timeout: int = 10) -> dict:
    """Run `code` against every hidden test of `problem` and report the result."""
    if not code or not code.strip():
        return {"problem_id": problem.id, "error": "There is no code to run."}
    if not code_execution_allowed():
        return {
            "problem_id": problem.id,
            "title": problem.title,
            "error": "Code execution is disabled (ALLOW_CODE_EXEC=0).",
            "verdict": "DISABLED",
        }

    cases = [{"args": args, "expected": expected} for args, expected in problem.tests]
    payload = {"func": problem.func, "args": problem.args, "cases": cases}

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "solution.py").write_text(code, encoding="utf-8")
        (base / "cases.json").write_text(json.dumps(payload), encoding="utf-8")
        (base / "runner.py").write_text(RUNNER, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, "-I", "runner.py"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_clean_env(),
            )
        except subprocess.TimeoutExpired:
            return {
                "problem_id": problem.id,
                "title": problem.title,
                "error": "Your code did not finish within %ss - maybe an infinite loop." % timeout,
                "verdict": "TIMEOUT",
            }

        result_file = base / "result.json"
        if not result_file.exists():
            return {
                "problem_id": problem.id,
                "title": problem.title,
                "error": "The grader could not run your code.",
                "stderr": (proc.stderr or "")[-800:],
                "verdict": "ERROR",
            }
        data = json.loads(result_file.read_text(encoding="utf-8"))

    passed = int(data.get("passed", 0))
    total = int(data.get("total", 0))
    if data.get("error"):
        verdict = "ERROR"
    elif total and passed == total:
        verdict = "PASS"
    elif passed:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    return {
        "problem_id": problem.id,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "passed": passed,
        "total": total,
        "verdict": verdict,
        "error": data.get("error"),
        "results": data.get("results", []),
        "hint": problem.hints[0] if (verdict in {"FAIL", "PARTIAL"} and problem.hints) else None,
    }
