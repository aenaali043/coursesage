"""Interview-style practice problems, each grounded in a chapter of the course.

Every problem names the chapter that teaches the concept, so the agent can cite
the exact video timestamp next to the exercise instead of guessing one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import timestamp_link


@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    difficulty: str
    concept: str
    chapter: str
    statement: str
    func: str
    args: str
    examples: tuple[tuple[str, str], ...]
    tests: tuple[tuple[str, str], ...]
    hints: tuple[str, ...]
    starter: str

    @property
    def call(self) -> str:
        return f"{self.func}({self.args})"

    def to_dict(self, with_hints: bool = True) -> dict:
        data = {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "concept": self.concept,
            "chapter": self.chapter,
            "signature": f"{self.func}({self.args})",
            "statement": self.statement,
            "examples": [{"call": c, "expected": e} for c, e in self.examples],
            "starter": self.starter,
        }
        if with_hints:
            data["hints"] = list(self.hints)
        return data


PROBLEMS: tuple[Problem, ...] = (
    Problem(
        id="sum-even",
        title="Sum of the even numbers",
        difficulty="easy",
        concept="lists and for loops",
        chapter="Lists: characteristics & operations",
        statement=(
            "Given a list of integers, return the sum of only the even ones. "
            "An empty list sums to 0."
        ),
        func="sum_even",
        args="nums",
        examples=(("sum_even([2, 4, 6, 7])", "12"), ("sum_even([])", "0")),
        tests=(
            ("([2, 4, 6, 7],)", "12"),
            ("([],)", "0"),
            ("([1, 3, 5],)", "0"),
            ("([10, 1, 4, 3, 2],)", "16"),
            ("([-2, -4, 5],)", "-6"),
        ),
        hints=(
            "Loop over the list once and keep a running total.",
            "A number is even when number % 2 == 0.",
        ),
        starter="def sum_even(nums):\n    total = 0\n    # your code here\n    return total\n",
    ),
    Problem(
        id="count-vowels",
        title="Count the vowels",
        difficulty="easy",
        concept="strings and string methods",
        chapter="String functions & methods",
        statement=(
            "Given a string, count how many characters are vowels (a, e, i, o, u). "
            "Upper and lower case both count."
        ),
        func="count_vowels",
        args="text",
        examples=(("count_vowels('hello')", "2"), ("count_vowels('xyz')", "0")),
        tests=(
            ("('hello',)", "2"),
            ("('xyz',)", "0"),
            ("('AEIOU aeiou',)", "10"),
            ("('',)", "0"),
            ("('rhythm',)", "0"),
        ),
        hints=(
            "A vowel belongs to the set {'a', 'e', 'i', 'o', 'u'}.",
            "text.lower() first so you only compare against lower case.",
        ),
        starter="def count_vowels(text):\n    count = 0\n    # your code here\n    return count\n",
    ),
    Problem(
        id="second-largest",
        title="Second largest distinct number",
        difficulty="easy",
        concept="list functions",
        chapter="Functions on lists",
        statement=(
            "Given a list of integers, return the second largest DISTINCT number. "
            "If it does not exist, return None. Do not use the max() function."
        ),
        func="second_largest",
        args="nums",
        examples=(("second_largest([1, 3, 2])", "2"), ("second_largest([5, 5])", "None")),
        tests=(
            ("([1, 3, 2],)", "2"),
            ("([5, 5, 1],)", "1"),
            ("([2, 1],)", "1"),
            ("([10, 9, 8, 7],)", "9"),
            ("([-1, -2, -3],)", "-2"),
            ("([5, 5],)", "None"),
            ("([7],)", "None"),
        ),
        hints=(
            "Keep the two biggest values you have seen so far.",
            "A value equal to the current biggest must not replace the second biggest.",
        ),
        starter="def second_largest(nums):\n    best = None\n    second = None\n    # your code here\n    return second\n",
    ),
    Problem(
        id="reverse-words",
        title="Reverse the word order",
        difficulty="easy",
        concept="slicing and split",
        chapter="Slicing & step (stride)",
        statement=(
            "Given a sentence, return it with the words in reverse order, "
            "separated by a single space."
        ),
        func="reverse_words",
        args="sentence",
        examples=(("reverse_words('hello world')", "'world hello'"), ("reverse_words('solo')", "'solo'")),
        tests=(
            ("('hello world',)", "'world hello'"),
            ("('a b c',)", "'c b a'"),
            ("('solo',)", "'solo'"),
            ("('  hi  there ',)", "'there hi'"),
            ("('',)", "''"),
        ),
        hints=(
            "sentence.split() gives you the words without extra spaces.",
            "Reversing a list is words[::-1].",
        ),
        starter="def reverse_words(sentence):\n    # your code here\n    return ''\n",
    ),
    Problem(
        id="invert-dict",
        title="Invert a dictionary",
        difficulty="easy",
        concept="dictionaries",
        chapter="Dictionaries",
        statement=(
            "Given a dictionary of string keys and integer values, return a new dictionary "
            "with the keys and values swapped - the integer values become string keys."
        ),
        func="invert_dict",
        args="data",
        examples=(("invert_dict({'a': 1})", "{'1': 'a'}"), ("invert_dict({})", "{}")),
        tests=(
            ("({'a': 1, 'b': 2},)", "{'1': 'a', '2': 'b'}"),
            ("({},)", "{}"),
            ("({'x': 7},)", "{'7': 'x'}"),
            ("({'a': 1, 'b': 2, 'c': 3},)", "{'1': 'a', '2': 'b', '3': 'c'}"),
        ),
        hints=(
            "A dict comprehension {k: v for ...} builds this in one line.",
            "Iterate over data.items() so you get key and value together.",
        ),
        starter="def invert_dict(data):\n    # your code here\n    return {}\n",
    ),
    Problem(
        id="two-sum",
        title="Two sum, indices returned",
        difficulty="medium",
        concept="dictionaries and lists",
        chapter="Dictionaries",
        statement=(
            "Given a list of integers nums and a target, return the two indices i < j of the "
            "FIRST pair (smallest i) where nums[i] + nums[j] == target. Return them in a list. "
            "A hash map of value -> index makes this linear."
        ),
        func="two_sum",
        args="nums, target",
        examples=(
            ("two_sum([2, 7, 11, 15], 9)", "[0, 1]"),
            ("two_sum([3, 2, 4], 6)", "[1, 2]"),
        ),
        tests=(
            ("([2, 7, 11, 15], 9)", "[0, 1]"),
            ("([3, 2, 4], 6)", "[1, 2]"),
            ("([3, 3], 6)", "[0, 1]"),
            ("([1, 2, 3], 5)", "[1, 2]"),
            ("([5, 5, 5], 10)", "[0, 1]"),
        ),
        hints=(
            "Walk the list once; for each number look for target - number in a dict of seen values.",
            "Store the index of every value you have already seen, not just the first one.",
        ),
        starter="def two_sum(nums, target):\n    seen = {}\n    # your code here\n    return []\n",
    ),
    Problem(
        id="group-anagrams",
        title="Group the anagrams",
        difficulty="medium",
        concept="dictionaries and sorting",
        chapter="Dictionaries",
        statement=(
            "Given a list of words, group the anagrams together. Return a list of groups where "
            "each group is sorted alphabetically, and the groups themselves are sorted by their "
            "smallest word."
        ),
        func="group_anagrams",
        args="words",
        examples=(
            ("group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat'])",
             "[['ate', 'eat', 'tea'], ['bat'], ['nat', 'tan']]"),
        ),
        tests=(
            ("(['eat', 'tea', 'tan', 'ate', 'nat', 'bat'],)", "[['ate', 'eat', 'tea'], ['bat'], ['nat', 'tan']]"),
            ("([],)", "[]"),
            ("(['a'],)", "[['a']]"),
            ("(['ab', 'ba', 'abc'],)", "[['ab', 'ba'], ['abc']]"),
        ),
        hints=(
            "sorted(word) is the same for every anagram, so it works as a dictionary key.",
            "The groups are plain lists, so you can sort them at the end.",
        ),
        starter="def group_anagrams(words):\n    groups = {}\n    # your code here\n    return []\n",
    ),
    Problem(
        id="flatten",
        title="Flatten a nested list",
        difficulty="medium",
        concept="nested loops and recursion",
        chapter="Nested loops & patterns",
        statement=(
            "Given a list that may contain other lists inside it, return a single flat list "
            "with all the values in order. Empty lists disappear."
        ),
        func="flatten",
        args="nested",
        examples=(("flatten([1, [2, [3, [4]]]])", "[1, 2, 3, 4]"), ("flatten([])", "[]")),
        tests=(
            ("([1, [2, [3, [4]]]],)", "[1, 2, 3, 4]"),
            ("([],)", "[]"),
            ("([1, 2, [3, 4]],)", "[1, 2, 3, 4]"),
            ("([[], [1]],)", "[1]"),
            ("([1, [2, 3], [[4]], []],)", "[1, 2, 3, 4]"),
        ),
        hints=(
            "For each item: if it is a list, flatten it and extend the result.",
            "A recursive helper handles lists nested any number of levels deep.",
        ),
        starter="def flatten(nested):\n    result = []\n    # your code here\n    return result\n",
    ),
    Problem(
        id="top-words",
        title="Top k frequent words",
        difficulty="medium",
        concept="dictionary comprehension and counting",
        chapter="Dictionary comprehension & JSON",
        statement=(
            "Given a sentence and a number k, return the k most frequent words as a list of "
            "[word, count] pairs. Sort by count descending, and for equal counts sort the "
            "word alphabetically."
        ),
        func="top_words",
        args="text, k",
        examples=(("top_words('a b a c b a', 2)", "[['a', 3], ['b', 2]]"), ("top_words('x', 1)", "[['x', 1]]")),
        tests=(
            ("('a b a c b a', 2)", "[['a', 3], ['b', 2]]"),
            ("('x', 1)", "[['x', 1]]"),
            ("('p q q p r', 2)", "[['p', 2], ['q', 2]]"),
            ("('one two one two three', 3)", "[['one', 2], ['two', 2], ['three', 1]]"),
            ("('a a b', 5)", "[['a', 2], ['b', 1]]"),
        ),
        hints=(
            "Count with a dictionary, then sort the items.",
            "sorted(items, key=lambda item: (-item[1], item[0])) gives you exactly that order.",
        ),
        starter="def top_words(text, k):\n    counts = {}\n    # your code here\n    return []\n",
    ),
    Problem(
        id="palindrome",
        title="Palindrome check",
        difficulty="medium",
        concept="strings, loops and conditions",
        chapter="Strings: basics",
        statement=(
            "Given a string, return True if it is a palindrome, ignoring case, spaces and "
            "punctuation. An empty string is a palindrome."
        ),
        func="is_palindrome",
        args="text",
        examples=(
            ("is_palindrome('A man, a plan, a canal: Panama')", "True"),
            ("is_palindrome('abc')", "False"),
        ),
        tests=(
            ("('A man, a plan, a canal: Panama',)", "True"),
            ("('',)", "True"),
            ("('abc',)", "False"),
            ("(\"No 'x' in Nixon\",)", "True"),
            ("('12321',)", "True"),
        ),
        hints=(
            "Keep only the letters and digits, then compare with the reversed string.",
            "str.isalnum() tells you if a character is a letter or a digit.",
        ),
        starter="def is_palindrome(text):\n    # your code here\n    return False\n",
    ),
    Problem(
        id="fizzbuzz-list",
        title="FizzBuzz into a list",
        difficulty="medium",
        concept="loops and conditional chains",
        chapter="Nested loops & patterns",
        statement=(
            "Given n, return a list of n strings where each number becomes: "
            "'FizzBuzz' when divisible by both 3 and 5, 'Fizz' when divisible by 3, "
            "'Buzz' when divisible by 5, otherwise the number as a string."
        ),
        func="fizzbuzz_list",
        args="n",
        examples=(
            ("fizzbuzz_list(5)", "['1', '2', 'Fizz', '4', 'Buzz']"),
            ("fizzbuzz_list(3)", "['1', '2', 'Fizz']"),
        ),
        tests=(
            ("(5,)", "['1', '2', 'Fizz', '4', 'Buzz']"),
            ("(3,)", "['1', '2', 'Fizz']"),
            ("(0,)", "[]"),
            ("(1,)", "['1']"),
            ("(15,)", "['1', '2', 'Fizz', '4', 'Buzz', 'Fizz', '7', '8', 'Fizz', 'Buzz', "
                      "'11', 'Fizz', '13', '14', 'FizzBuzz']"),
        ),
        hints=(
            "Check divisibility by 15 first, otherwise Fizz and Buzz overwrite each other.",
            "Use range(1, n + 1) so n itself is included.",
        ),
        starter="def fizzbuzz_list(n):\n    result = []\n    # your code here\n    return result\n",
    ),
    Problem(
        id="rotate-list",
        title="Rotate a list to the right",
        difficulty="hard",
        concept="slicing and modulo",
        chapter="Slicing & step (stride)",
        statement=(
            "Given a list and a number k, return the list rotated k positions to the right. "
            "k can be larger than the length of the list."
        ),
        func="rotate_list",
        args="nums, k",
        examples=(
            ("rotate_list([1, 2, 3, 4, 5], 2)", "[4, 5, 1, 2, 3]"),
            ("rotate_list([1, 2, 3], 0)", "[1, 2, 3]"),
        ),
        tests=(
            ("([1, 2, 3, 4, 5], 2)", "[4, 5, 1, 2, 3]"),
            ("([1, 2, 3], 0)", "[1, 2, 3]"),
            ("([], 0)", "[]"),
            ("([1, 2, 3, 4], 1)", "[4, 1, 2, 3]"),
            ("([1, 2, 3], 4)", "[3, 1, 2]"),
        ),
        hints=(
            "Rotating by len(nums) changes nothing, so reduce k with the modulo operator.",
            "The last k elements move to the front: nums[-k:] + nums[:-k].",
        ),
        starter="def rotate_list(nums, k):\n    # your code here\n    return []\n",
    ),
    Problem(
        id="merge-intervals",
        title="Merge overlapping intervals",
        difficulty="hard",
        concept="sorting and list building",
        chapter="List methods",
        statement=(
            "Given a list of [start, end] intervals, merge every overlapping pair and return "
            "the merged intervals sorted by start. Touching intervals also merge."
        ),
        func="merge_intervals",
        args="intervals",
        examples=(
            ("merge_intervals([[1, 3], [2, 6], [8, 10]])", "[[1, 6], [8, 10]]"),
            ("merge_intervals([[1, 4], [4, 5]])", "[[1, 5]]"),
        ),
        tests=(
            ("([[1, 3], [2, 6], [8, 10], [15, 18]],)", "[[1, 6], [8, 10], [15, 18]]"),
            ("([[1, 4], [4, 5]],)", "[[1, 5]]"),
            ("([[1, 4], [0, 4]],)", "[[0, 4]]"),
            ("([[1, 4], [2, 3]],)", "[[1, 4]]"),
            ("([],)", "[]"),
        ),
        hints=(
            "Sort the intervals by their start before you compare neighbours.",
            "If the next interval starts before the current one ends, extend the current end.",
        ),
        starter="def merge_intervals(intervals):\n    merged = []\n    # your code here\n    return merged\n",
    ),
    Problem(
        id="transpose",
        title="Transpose a matrix",
        difficulty="hard",
        concept="nested loops",
        chapter="Nested loops & patterns",
        statement=(
            "Given a list of rows (a matrix), return its transpose: the rows become the "
            "columns. Every inner list must have the same length."
        ),
        func="transpose",
        args="matrix",
        examples=(
            ("transpose([[1, 2, 3], [4, 5, 6]])", "[[1, 4], [2, 5], [3, 6]]"),
            ("transpose([[1]])", "[[1]]"),
        ),
        tests=(
            ("([[1, 2, 3], [4, 5, 6]],)", "[[1, 4], [2, 5], [3, 6]]"),
            ("([[1]],)", "[[1]]"),
            ("([[1, 2], [3, 4], [5, 6]],)", "[[1, 3, 5], [2, 4, 6]]"),
            ("([],)", "[]"),
        ),
        hints=(
            "The result has len(matrix[0]) rows and len(matrix) columns.",
            "Build one row at a time by picking the same column from every input row.",
        ),
        starter="def transpose(matrix):\n    result = []\n    # your code here\n    return result\n",
    ),
)


def get_problem(problem_id: str) -> Problem | None:
    key = (problem_id or "").strip().lower()
    for problem in PROBLEMS:
        if problem.id == key:
            return problem
    return None


def list_problems(
    topic: str | None = None,
    difficulty: str | None = None,
    limit: int | None = None,
) -> list[Problem]:
    """Filter the bank by topic keyword and/or difficulty, preserving bank order."""
    rows = list(PROBLEMS)
    if difficulty:
        wanted = difficulty.strip().lower()
        rows = [p for p in rows if p.difficulty == wanted]
    if topic:
        needle = topic.strip().lower()
        if needle:
            rows = [
                p for p in rows
                if needle in p.concept.lower()
                or needle in p.title.lower()
                or needle in p.chapter.lower()
            ]
    if limit:
        rows = rows[: max(1, int(limit))]
    return rows


def chapter_reference(kb, problem: Problem) -> dict:
    """Resolve the course chapter for a problem into a citable timestamp."""
    chapter = next((c for c in kb.chapters if c["title"] == problem.chapter), None)
    if not chapter:
        return {"chapter": problem.chapter, "start": None, "link": None}
    start = chapter["start"]
    seconds = int(start.split(":")[0]) * 3600 + int(start.split(":")[1]) * 60 + int(start.split(":")[2])
    return {"chapter": chapter["title"], "start": start, "link": timestamp_link(seconds)}


def format_problem_list(kb, rows: list[Problem]) -> str:
    """Render a numbered list of problems with the course timestamp for each."""
    if not rows:
        return "No problem matched that topic or difficulty. Try /problems with no filter, "
        "or a topic like lists, dictionaries, strings, loops."

    lines = [f"{len(rows)} practice problem(s) - interview style, grounded in the course:", ""]
    for index, problem in enumerate(rows, 1):
        ref = chapter_reference(kb, problem)
        where = ref["chapter"]
        if ref["start"]:
            where = f"{where} @ {ref['start']}"
            if ref["link"]:
                where = f"[{where}]({ref['link']})"
        lines.append(f"{index}. [{problem.difficulty}] {problem.id} - {problem.title}")
        lines.append(f"   concept : {problem.concept}")
        lines.append(f"   course  : {where}")
        lines.append(f"   write   : {problem.func}({problem.args})")
        lines.append(f"   task    : {problem.statement}")
        for call, expected in problem.examples[:1]:
            lines.append(f"   example : {call} -> {expected}")
        lines.append("")
    lines.append("Write your solution, then paste it back with:  /grade <problem-id>")
    lines.append("Need a nudge? Ask for a hint for that problem id.")
    return "\n".join(lines)


def format_grade(result: dict) -> str:
    """Render a grading result as readable feedback."""
    if result.get("error") and not result.get("total"):
        return f"Could not grade `{result.get('problem_id', '?')}`: {result['error']}"

    lines = [f"**{result.get('problem_id')}** - {result.get('passed')}/{result.get('total')} tests passed ({result.get('verdict')})"]
    if result.get("error"):
        lines.append(f"error: {result['error']}")
    for row in result.get("results", []):
        status = row.get("status")
        if status == "pass":
            lines.append(f"  test {row['test']}: pass")
        elif status == "fail":
            lines.append(
                f"  test {row['test']}: FAIL  input {row.get('input')} "
                f"-> expected {row.get('expected')}, got {row.get('got')}"
            )
        else:
            lines.append(f"  test {row['test']}: error {row.get('detail', '')}")
    if result.get("hint"):
        lines.append(f"hint: {result['hint']}")
    return "\n".join(lines)

