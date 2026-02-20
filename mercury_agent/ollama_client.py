"""Ollama API provider — local models via Ollama."""

from __future__ import annotations

import json
from typing import Any, Generator

import requests

from .provider import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3") -> None:
        super().__init__(model)
        self._host = host.rstrip("/")
        self._supports_tools: bool | None = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    def supports_tools(self) -> bool:
        if self._supports_tools is not None:
            return self._supports_tools
        try:
            resp = requests.post(
                f"{self._host}/api/show",
                json={"name": self.model},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                template = data.get("template", "")
                model_info = data.get("model_info", {})
                has_tools = "tools" in template.lower() or "tool" in json.dumps(model_info).lower()
                self._supports_tools = has_tools
            else:
                self._supports_tools = False
        except requests.RequestException:
            self._supports_tools = False
        return self._supports_tools

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if stream:
            return self._stream(payload)
        return self._blocking(payload)

    def _check_404(self, resp: requests.Response, payload: dict[str, Any]) -> None:
        if resp.status_code == 404:
            model = payload.get("model", "?")
            available = self.list_models()
            msg = f"Model '{model}' not found in Ollama."
            if available:
                msg += f" Available: {', '.join(available)}"
            msg += f"\nPull it first: ollama pull {model}"
            raise RuntimeError(msg)

    def _blocking(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(
            f"{self._host}/api/chat",
            json=payload,
            timeout=(10, 600),
        )
        self._check_404(resp, payload)
        resp.raise_for_status()
        return resp.json()

    def _stream(self, payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        resp = requests.post(
            f"{self._host}/api/chat",
            json=payload,
            stream=True,
            timeout=(10, 600),
        )
        self._check_404(resp, payload)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield json.loads(line)

    def set_model(self, model: str) -> None:
        self.model = model
        self._supports_tools = None

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self._host}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self._host}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except requests.RequestException:
            return []


# Backward compat alias
OllamaClient = OllamaProvider
