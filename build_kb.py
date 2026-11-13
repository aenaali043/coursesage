"""Rebuild the course knowledge base from the raw transcript.

Usage:
    python build_kb.py

Input : data/transcript_raw.json   (list of {start, end, text} segments)
        data/chapters.json         (curated chapter map)
Output: data/course_chunks.json    (timestamped, chapter-tagged chunks for retrieval)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TARGET_CHARS = 1600
MAX_CHARS = 2200


def to_seconds(ts: str) -> int:
    h, m, s = (int(p) for p in ts.split(":"))
    return h * 3600 + m * 60 + s


def to_timestamp(sec: int) -> str:
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # collapse the most common auto-caption stutters: "the the" -> "the"
    text = re.sub(r"\b(\w+)( \1\b)+", r"\1", text, flags=re.IGNORECASE)
    return text


def load_chapters() -> list[dict]:
    chapters = json.loads((DATA / "chapters.json").read_text(encoding="utf-8"))
    for c in chapters:
        c["start_sec"] = to_seconds(c["start"])
    return sorted(chapters, key=lambda c: c["start_sec"])


def chapter_for(sec: int, chapters: list[dict]) -> dict:
    current = chapters[0]
    for c in chapters:
        if c["start_sec"] <= sec:
            current = c
        else:
            break
    return current


def build_chunks(segments: list[dict], chapters: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    buf: list[dict] = []

    def flush():
        if not buf:
            return
        start = buf[0]["start"]
        end = buf[-1]["end"]
        start_sec = to_seconds(start)
        chapter = chapter_for(start_sec, chapters)
        text = clean(" ".join(s["text"] for s in buf))
        chunks.append(
            {
                "id": f"c{len(chunks):04d}",
                "start": start,
                "end": end,
                "start_sec": start_sec,
                "end_sec": to_seconds(end),
                "chapter": chapter["title"],
                "track": chapter["track"],
                "text": text,
            }
        )

    for seg in segments:
        if not seg.get("text"):
            continue
        seg_chapter = chapter_for(to_seconds(seg["start"]), chapters)["title"]
        pending = sum(len(s["text"]) for s in buf)
        if buf and (pending >= TARGET_CHARS or seg_chapter != buf[0].get("_chapter")):
            flush()
            buf = []
        seg = {**seg, "_chapter": seg_chapter}
        buf.append(seg)

    flush()
    return chunks


def main() -> None:
    segments = json.loads((DATA / "transcript_raw.json").read_text(encoding="utf-8"))
    chapters = load_chapters()
    chunks = build_chunks(segments, chapters)
    (DATA / "course_chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    total = sum(len(c["text"]) for c in chunks)
    print(f"segments={len(segments)} chunks={len(chunks)} chars={total}")
    print(f"duration={to_timestamp(chunks[-1]['end_sec'])}")


if __name__ == "__main__":
    main()
