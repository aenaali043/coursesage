"""Retrieval layer: BM25 over timestamped transcript chunks + chapter index.

Pure standard library, so the agent works with no vector DB and no extra deps.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_DIR, timestamp_link

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "of", "to", "in", "on",
    "for", "with", "is", "are", "was", "were", "be", "been", "being", "it", "its",
    "this", "that", "these", "those", "i", "you", "we", "they", "he", "she", "my",
    "your", "our", "their", "me", "us", "them", "as", "at", "by", "from", "not",
    "do", "does", "did", "can", "could", "will", "would", "should", "what", "how",
    "why", "when", "which", "who", "there", "here", "about", "into", "than", "up",
}

SYNONYMS = {
    "append": ["append", "extend", "insert"],
    "difference": ["difference", "diff", "subtract"],
    "array": ["list", "array"],
    "dict": ["dictionary", "dict"],
    "fn": ["function", "def"],
    "func": ["function", "def"],
    "loop": ["loop", "for", "while", "iterate", "iteration"],
    "llm": ["llm", "model", "gpt", "transformer"],
    "embedding": ["embedding", "vector", "vectorization"],
    "rag": ["rag", "retrieval", "vector", "document"],
    "callback": ["function", "argument", "higher order"],
    "mutable": ["mutable", "immutable", "memory", "reference"],
    "quiz": ["question", "practice", "assignment"],
    # the transcript is auto-captioned, so several Python spellings never appear
    # literally: *args becomes "arcs/ars", **kwargs becomes "kwords/kwax".
    "kwargs": ["keyword", "argument", "dictionary", "kwords"],
    "kwarg": ["keyword", "argument", "dictionary", "kwords"],
    "args": ["argument", "arcs", "ars"],
    "arg": ["argument", "arcs"],
    "elif": ["elif", "else", "excel"],
    "fstring": ["format", "f", "string"],
    "docstring": ["doc", "string", "function"],
    "dunder": ["method", "inbuilt"],
    "nested": ["nested", "inner", "outer"],
    "alias": ["alias", "address", "copy"],
    "aliasing": ["alias", "address", "copy"],
    "crud": ["operation", "list", "dictionary"],
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    out: list[str] = []
    for w in words:
        if w in STOPWORDS or len(w) < 2:
            continue
        out.append(w)
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            out.append(w[:-1])
    return out


@dataclass
class Hit:
    chunk: dict
    score: float

    @property
    def link(self) -> str:
        return timestamp_link(self.chunk["start_sec"])

    def to_dict(self) -> dict:
        return {
            "start": self.chunk["start"],
            "end": self.chunk["end"],
            "chapter": self.chunk["chapter"],
            "track": self.chunk["track"],
            "link": self.link,
            "score": round(self.score, 3),
            "text": self.chunk["text"],
        }


class CourseKB:
    def __init__(self, chunks_path: Path | None = None, chapters_path: Path | None = None):
        chunks_path = chunks_path or DATA_DIR / "course_chunks.json"
        chapters_path = chapters_path or DATA_DIR / "chapters.json"
        self.chunks: list[dict] = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.chapters: list[dict] = json.loads(chapters_path.read_text(encoding="utf-8"))

        self._docs: list[Counter] = []
        self._lengths: list[int] = []
        df: Counter = Counter()
        for chunk in self.chunks:
            tokens = tokenize(chunk["text"] + " " + chunk["chapter"])
            chunk["_tokens"] = tokens  # cached for query expansion
            counter = Counter(tokens)
            self._docs.append(counter)
            self._lengths.append(len(tokens))
            df.update(counter.keys())
            chunk.pop("_tokens")

        self._df = df
        self._n = len(self.chunks)
        self._avgdl = sum(self._lengths) / max(self._n, 1)
        self._chapter_index = {
            c["title"]: {
                "title_tokens": set(tokenize(c["title"])),
                "desc_tokens": set(tokenize(c["desc"])),
            }
            for c in self.chapters
        }

    # ------------------------------------------------------------------ search
    def _idf(self, term: str) -> float:
        n_q = self._df.get(term, 0)
        return math.log(1 + (self._n - n_q + 0.5) / (n_q + 0.5))

    def search(
        self,
        query: str,
        k: int = 5,
        track: str | None = None,
        min_score: float = 0.0,
    ) -> list[Hit]:
        terms = tokenize(query)
        expanded: list[str] = []
        for t in terms:
            expanded.append(t)
            expanded.extend(SYNONYMS.get(t, []))
        if not expanded:
            return []

        query_counts = Counter(expanded)
        unique_terms = set(expanded)
        k1, b = 1.5, 0.75
        scored: list[tuple[float, int]] = []
        track_filter = (track or "").strip().lower()

        for idx, doc in enumerate(self._docs):
            if track_filter and self.chunks[idx]["track"].lower() != track_filter:
                continue
            dl = self._lengths[idx]
            score = 0.0
            matched: set[str] = set()
            for term, qtf in query_counts.items():
                tf = doc.get(term)
                if not tf:
                    continue
                denom = tf + k1 * (1 - b + b * dl / self._avgdl)
                score += self._idf(term) * (tf * (k1 + 1) / denom) * (1 + 0.15 * (qtf - 1))
                matched.add(term)
            if score <= 0:
                continue
            # reward passages that cover more of the question, not just one rare word
            coverage = len(matched & unique_terms) / max(len(unique_terms), 1)
            score *= 0.55 + 0.45 * coverage
            # reward passages from a chapter whose title (strongly) or description
            # (weakly) matches the question, so topic words pick the right section
            chapter = self._chapter_index.get(self.chunks[idx]["chapter"], {})
            score += 1.4 * len(matched & chapter.get("title_tokens", set()))
            score += 0.45 * len(matched & chapter.get("desc_tokens", set()))
            scored.append((score, idx))

        scored.sort(reverse=True)
        hits: list[Hit] = []
        per_chapter: Counter = Counter()
        for score, idx in scored:
            if score < min_score:
                break
            chapter = self.chunks[idx]["chapter"]
            if per_chapter[chapter] >= 2:  # keep results diverse across chapters
                continue
            per_chapter[chapter] += 1
            hits.append(Hit(self.chunks[idx], score))
            if len(hits) >= k:
                break
        return hits

    # ----------------------------------------------------------------- outline
    def outline(self, track: str | None = None) -> list[dict]:
        rows = []
        for c in self.chapters:
            if track and c["track"].lower() != track.strip().lower():
                continue
            rows.append(
                {
                    "start": c["start"],
                    "chapter": c["title"],
                    "track": c["track"],
                    "covers": c["desc"],
                    "link": timestamp_link(int(c["start"].split(":")[0]) * 3600
                                           + int(c["start"].split(":")[1]) * 60
                                           + int(c["start"].split(":")[2])),
                }
            )
        return rows

    # ------------------------------------------------------- transcript window
    def chapter_at(self, sec: int) -> dict | None:
        chapters = sorted(
            (
                (parse_timestamp(c["start"]), c)
                for c in self.chapters
            ),
            key=lambda pair: pair[0],
        )
        current = chapters[0][1] if chapters else None
        for start_sec, chapter in chapters:
            if start_sec <= sec:
                current = chapter
            else:
                break
        return current

    def window_at(self, start_sec: int, minutes: int = 3) -> dict:
        end_sec = start_sec + minutes * 60
        picked = [c for c in self.chunks if c["end_sec"] >= start_sec and c["start_sec"] <= end_sec]
        chapter = self.chapter_at(start_sec)
        if not picked:
            return {"start_sec": start_sec, "text": "", "chapter": chapter["title"] if chapter else None}
        return {
            "start": picked[0]["start"],
            "end": picked[-1]["end"],
            "start_sec": picked[0]["start_sec"],
            "chapter": chapter["title"] if chapter else picked[0]["chapter"],
            "link": timestamp_link(start_sec),
            "text": " ".join(c["text"] for c in picked),
        }

    def stats(self) -> dict:
        return {
            "chunks": len(self.chunks),
            "chapters": len(self.chapters),
            "chars": sum(len(c["text"]) for c in self.chunks),
            "duration": self.chunks[-1]["end"],
        }


def parse_timestamp(value: str | int) -> int:
    """Accepts 754, '754', '12:34' or '0:12:34'."""
    if isinstance(value, int):
        return value
    value = str(value).strip()
    if value.replace(".", "", 1).isdigit():
        return int(float(value))
    parts = [int(p) for p in value.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
