"""OpenRouter API client for Clanker.

This client is used to query an LLM (e.g., Devstral free tier) to decide actions.

Auth:
- Set environment variable OPENROUTER_API_KEY

Docs:
- https://openrouter.ai/docs
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class OpenRouterConfig:
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "mistralai/devstral-small:free"
    timeout_s: int = 20
    max_retries: int = 2
    temperature: float = 0.2
    site_url: Optional[str] = None
    app_name: Optional[str] = None


class OpenRouterClient:
    """Minimal OpenRouter chat-completions client."""

    def __init__(self, config: OpenRouterConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        # Allow optional metadata via env vars (nice for OpenRouter dashboards)
        if self.config.site_url is None:
            self.config.site_url = os.getenv("OPENROUTER_SITE_URL")
        if self.config.app_name is None:
            self.config.app_name = os.getenv("OPENROUTER_APP_NAME")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Optional OpenRouter headers
        if self.config.site_url:
            headers["HTTP-Referer"] = self.config.site_url
        if self.config.app_name:
            headers["X-Title"] = self.config.app_name
        return headers

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send a chat request and return the assistant content as text."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        last_err: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                resp = requests.post(
                    url,
                    headers=self._headers(),
                    data=json.dumps(payload),
                    timeout=self.config.timeout_s,
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:400]}")

                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = message.get("content")
                if not isinstance(content, str):
                    raise RuntimeError(f"Unexpected OpenRouter response shape: {data}")
                return content
            except Exception as e:
                last_err = e
                backoff = min(2.0, 0.25 * (2**attempt))
                logger.warning(f"OpenRouter request failed (attempt {attempt + 1}): {e}")
                time.sleep(backoff)

        raise RuntimeError(f"OpenRouter request failed after retries: {last_err}")

