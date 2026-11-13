"""Tiny OpenAI-compatible chat client (urllib only, no SDK required).

Works with OpenAI, Google Gemini (OpenAI-compat endpoint), Groq, OpenRouter,
Ollama and any other server that speaks /chat/completions.
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from typing import Any

from .config import Settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    # alternate models to try when the primary one is rate-limited (429)
    FALLBACK_MODELS = {
        "gemini": ["gemini-3-flash-preview", "gemini-flash-lite-latest"],
    }

    def __init__(self, settings: Settings, timeout: int = 120):
        self.settings = settings
        self.timeout = timeout
        if not settings.api_key and settings.provider != "ollama":
            raise LLMError(
                f"No API key found for provider '{settings.provider}'. "
                "Set it in .env (see .env.example) before running the agent."
            )

    # ------------------------------------------------------------------ public
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
    ) -> dict:
        models = [self.settings.model]
        models += [m for m in self.FALLBACK_MODELS.get(self.settings.provider, []) if m != self.settings.model]

        last_error: Exception | None = None
        for model in models:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": self.settings.temperature if temperature is None else temperature,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            for attempt in range(2):
                try:
                    data = self._post(payload)
                    return data["choices"][0]["message"]
                except urllib.error.HTTPError as exc:
                    body = exc.read().decode("utf-8", "ignore")[:600]
                    last_error = LLMError(f"HTTP {exc.code} from {self.settings.base_url}: {body}")
                    if exc.code in (429, 500, 502, 503, 504):
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise last_error from exc
                except (urllib.error.URLError, TimeoutError, KeyError, http.client.RemoteDisconnected) as exc:
                    last_error = LLMError(f"Request to {self.settings.base_url} failed: {exc}")
                    time.sleep(1.5 * (attempt + 1))
        raise last_error or LLMError("Unknown LLM failure")

    # ------------------------------------------------------------------ internal
    def _post(self, payload: dict) -> dict:
        url = f"{self.settings.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self.settings.api_key}")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
