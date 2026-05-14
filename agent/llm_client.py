"""
LLM Client — strictly uses Groq.
Callers use OpenAI chat completions format with tools support.
"""

import os, logging
from openai import OpenAI

logger = logging.getLogger(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class LLMClient:
    """
    Client for interacting with Groq. Requires dynamic configuration of API key.
    All calls use OpenAI chat completions format with tools support.
    """

    def __init__(self):
        self._client = None
        self.active_backend = "groq"
        env_key = os.getenv("GROQ_API_KEY")
        if env_key:
            self.set_api_key(env_key)
        
    def set_api_key(self, api_key: str):
        if api_key:
            self._client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
            logger.info("Groq API Key configured successfully")
        else:
            self._client = None

    def is_configured(self) -> bool:
        return self._client is not None

    def chat(self, messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.2):
        if not self._client:
            raise ValueError("Groq API Key is not configured. Please set it in the Dashboard.")
            
        kwargs = {
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self._client.chat.completions.create(
            model=GROQ_MODEL,
            **kwargs,
        )

    def is_using_fallback(self) -> bool:
        return False

    def health_check(self) -> dict:
        """Returns { "groq": "configured"|"missing", "active": "groq" }"""
        return {
            "groq": "configured" if self._client else "missing",
            "active": self.active_backend
        }
