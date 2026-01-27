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
    model: str = "google/gemini-2.0-flash-exp:free"
    fallback_models: List[str] = None # List of backup models
    timeout_s: int = 20
    max_retries: int = 2
    temperature: float = 0.2
    site_url: Optional[str] = None
    app_name: Optional[str] = None


class OpenRouterClient:
    """Generic OpenAI-compatible LLM client with automatic model fallback."""

    def __init__(self, config: OpenRouterConfig, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("EDENAI_API_KEY")
        self.all_models = [config.model]
        if config.fallback_models:
            self.all_models.extend(config.fallback_models)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.site_url:
            headers["HTTP-Referer"] = self.config.site_url
        if self.config.app_name:
            headers["X-Title"] = self.config.app_name
        return headers

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send a chat request with automatic fallback through the model list."""
        if not self.api_key:
            raise RuntimeError("No API key found")

        last_err: Optional[Exception] = None
        
        # Try each model in the list
        for model_name in self.all_models:
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "temperature": self.config.temperature,
            }

            for attempt in range(self.config.max_retries + 1):
                try:
                    logger.info(f"Querying LLM: {model_name} (Attempt {attempt+1})")
                    resp = requests.post(
                        url,
                        headers=self._headers(),
                        data=json.dumps(payload),
                        timeout=self.config.timeout_s,
                    )
                    
                    if resp.status_code == 429:
                        logger.warning(f"Rate Limit on {model_name}, moving to fallback immediately.")
                        break # Break retry loop, try NEXT model in fallback list
                    
                    if resp.status_code == 404:
                        logger.warning(f"Model {model_name} not found (404), skipping.")
                        break # Skip this model entirely
                    
                    if resp.status_code >= 400:
                        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

                    data = resp.json()
                    if "choices" in data:
                        content = data["choices"][0].get("message", {}).get("content")
                        # Handle models that wrap content in reasoning or think tags
                        if content and isinstance(content, str):
                            if "</thought>" in content:
                                content = content.split("</thought>")[-1].strip()
                            elif "</think>" in content:
                                content = content.split("</think>")[-1].strip()
                            elif "<think>" in content: # Handle unclosed think tag
                                content = content.split("<think>")[-1].split("</think>")[-1].strip()
                            return content.strip()
                    
                    raise RuntimeError(f"Invalid response shape from {model_name}")
                except Exception as e:
                    last_err = e
                    logger.warning(f"Request failed for {model_name}: {e}")
                    if attempt < self.config.max_retries:
                        time.sleep(0.5 * (2**attempt))
            
            logger.error(f"Model {model_name} exhausted, trying next model in fallback list...")

        raise RuntimeError(f"All models failed. Last error: {last_err}")

