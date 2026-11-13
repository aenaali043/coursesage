"""Configuration: provider presets, .env loading, runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

VIDEO_ID = "J9BI0jGOds8"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


def timestamp_link(seconds: int) -> str:
    return f"{VIDEO_URL}&t={int(seconds)}s"


PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-3.1-flash-lite",
        "key_env": "GEMINI_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "key_env": "OLLAMA_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "key_env": "OPENROUTER_API_KEY",
    },
}


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader so the project has zero config dependencies."""
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    provider: str = "openai"
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.3
    max_steps: int = 6
    tool_mode: str = "auto"  # auto | native | text
    top_k: int = 5
    verbose: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
        preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["openai"])
        api_key = (
            os.environ.get("LLM_API_KEY")
            or os.environ.get(preset["key_env"])
            or ("ollama" if provider == "ollama" else "")
        )
        return cls(
            provider=provider,
            model=os.environ.get("LLM_MODEL") or preset["model"],
            base_url=(os.environ.get("LLM_BASE_URL") or preset["base_url"]).rstrip("/"),
            api_key=api_key,
            temperature=float(os.environ.get("LLM_TEMPERATURE", 0.3)),
            max_steps=int(os.environ.get("AGENT_MAX_STEPS", 6)),
            tool_mode=os.environ.get("TOOL_MODE", "auto").strip().lower(),
            top_k=int(os.environ.get("RETRIEVAL_TOP_K", 5)),
            verbose=os.environ.get("AGENT_VERBOSE", "0") in {"1", "true", "yes"},
        )

    def describe(self) -> str:
        return f"{self.provider} / {self.model} @ {self.base_url}"
