"""
LLM Client — wraps LM Studio (primary) and Groq (fallback).
Callers never know which backend is in use.
All calls use OpenAI chat completions format with tools support.
"""

import os, logging
from openai import OpenAI, APIConnectionError, APITimeoutError

logger = logging.getLogger(__name__)

LM_STUDIO_BASE = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen2.5-7b-instruct")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class LLMClient:
    """
    Wraps LM Studio (primary) and Groq (fallback).
    Callers never know which backend is in use.
    All calls use OpenAI chat completions format with tools support.
    """

    def __init__(self):
        self._primary = OpenAI(base_url=LM_STUDIO_BASE, api_key="lm-studio", timeout=15.0)
        self._fallback = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ.get("GROQ_API_KEY", ""))
        self.active_backend = "lm_studio"
        self._check_primary_health()

    def _check_primary_health(self):
        try:
            models = self._primary.models.list()
            if not models.data:
                raise RuntimeError("LM Studio has no models loaded")
            logger.info(f"LM Studio healthy. Loaded: {[m.id for m in models.data]}")
        except Exception as e:
            logger.warning(f"LM Studio unavailable ({e}). Starting on Groq fallback.")
            self.active_backend = "groq"

    def chat(self, messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.2):
        """
        Try primary first. On any exception (ConnectionError, Timeout,
        httpx.ConnectError, status >= 500), log the error, switch active_backend
        to "groq", and retry with fallback. If fallback also fails, raise.
        """
        kwargs = {
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        if self.active_backend == "lm_studio":
            try:
                return self._primary.chat.completions.create(
                    model=LM_STUDIO_MODEL,
                    **kwargs,
                )
            except (APIConnectionError, APITimeoutError, Exception) as e:
                logger.warning(f"LM Studio failed ({type(e).__name__}: {e}). Switching to Groq.")
                self.active_backend = "groq"

        # Groq fallback path
        return self._fallback.chat.completions.create(
            model=GROQ_MODEL,
            **kwargs,
        )

    def is_using_fallback(self) -> bool:
        return self.active_backend == "groq"

    def health_check(self) -> dict:
        """Returns { "primary": "ok"|"unavailable", "fallback": "ok"|"unavailable", "active": "lm_studio"|"groq" }"""
        primary_ok = "unavailable"
        try:
            self._primary.models.list()
            primary_ok = "ok"
        except Exception:
            pass
        return {"primary": primary_ok, "fallback": "ok", "active": self.active_backend}
