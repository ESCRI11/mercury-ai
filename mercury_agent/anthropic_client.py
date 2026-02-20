"""Anthropic API provider — Claude models via the Anthropic REST API."""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Generator

import requests

from .provider import BaseProvider

ANTHROPIC_API_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"

_RETRYABLE_STATUS = {429, 500, 502, 503, 529}
_MAX_RETRIES = 3
_RETRY_BACKOFF = [2, 5, 10]

KNOWN_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-haiku-4-20250414",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
]


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", base_url: str = ANTHROPIC_API_URL) -> None:
        super().__init__(model)
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def supports_tools(self) -> bool:
        return True

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
        system_text, api_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": 4096,
        }
        if system_text:
            payload["system"] = [
                {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}},
            ]
        if tools:
            payload["tools"] = self._convert_tools(tools)
        if stream:
            payload["stream"] = True
            return self._stream(payload)
        return self._blocking(payload)

    def _blocking(self, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(_MAX_RETRIES):
            t0 = time.time()
            try:
                resp = requests.post(
                    f"{self._base_url}/v1/messages",
                    headers=self._headers(),
                    json=payload,
                    timeout=(10, 300),
                )
                self._check_error(resp, raise_retryable=(attempt < _MAX_RETRIES - 1))
                elapsed_ns = int((time.time() - t0) * 1_000_000_000)
                data = resp.json()
                return self._normalize_response(data, elapsed_ns)
            except _RetryableError:
                time.sleep(_RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)])
        raise RuntimeError("Anthropic API: max retries exceeded")

    def _connect_stream(self, payload: dict[str, Any]) -> requests.Response:
        for attempt in range(_MAX_RETRIES):
            try:
                resp = requests.post(
                    f"{self._base_url}/v1/messages",
                    headers=self._headers(),
                    json=payload,
                    stream=True,
                    timeout=(10, 300),
                )
                self._check_error(resp, raise_retryable=(attempt < _MAX_RETRIES - 1))
                return resp
            except _RetryableError as e:
                wait = _RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)]
                print(f"  Anthropic overloaded, retrying in {wait}s... ({e.message})", file=sys.stderr)
                time.sleep(wait)
        raise RuntimeError("Anthropic API: max retries exceeded (overloaded)")

    def _stream(self, payload: dict[str, Any], _retries_left: int = _MAX_RETRIES) -> Generator[dict[str, Any], None, None]:
        resp = self._connect_stream(payload)

        input_tokens = 0
        output_tokens = 0
        cache_read = 0
        cache_creation = 0
        current_tool_name = ""
        current_tool_id = ""
        tool_json_buf = ""
        t0 = time.time()

        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if not line_str.startswith("data: "):
                    continue
                raw = line_str[6:]
                if raw.strip() == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                if event_type == "error":
                    err_data = event.get("error", {})
                    err_type = err_data.get("type", "unknown")
                    err_msg = err_data.get("message", raw)
                    if err_type in ("overloaded_error", "api_error"):
                        raise _RetryableError(529, f"{err_type}: {err_msg}")
                    raise RuntimeError(f"Anthropic stream error: {err_type} — {err_msg}")

                elif event_type == "message_start":
                    usage = event.get("message", {}).get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    cache_creation = usage.get("cache_creation_input_tokens", 0)

                elif event_type == "content_block_start":
                    block = event.get("content_block", {})
                    if block.get("type") == "tool_use":
                        current_tool_name = block.get("name", "")
                        current_tool_id = block.get("id", "")
                        tool_json_buf = ""

                elif event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield {"message": {"content": delta.get("text", "")}, "done": False}
                    elif delta.get("type") == "input_json_delta":
                        tool_json_buf += delta.get("partial_json", "")

                elif event_type == "content_block_stop":
                    if current_tool_name:
                        try:
                            args = json.loads(tool_json_buf) if tool_json_buf else {}
                        except json.JSONDecodeError:
                            args = {}
                        yield {
                            "message": {
                                "content": "",
                                "tool_calls": [{
                                    "function": {"name": current_tool_name, "arguments": args},
                                    "id": current_tool_id,
                                }],
                            },
                            "done": False,
                        }
                        current_tool_name = ""
                        tool_json_buf = ""

                elif event_type == "message_delta":
                    usage = event.get("usage", {})
                    output_tokens = usage.get("output_tokens", output_tokens)

                elif event_type == "message_stop":
                    elapsed_ns = int((time.time() - t0) * 1_000_000_000)
                    yield {
                        "message": {"content": ""},
                        "done": True,
                        "prompt_eval_count": input_tokens,
                        "eval_count": output_tokens,
                        "total_duration": elapsed_ns,
                        "prompt_eval_duration": 0,
                        "eval_duration": elapsed_ns,
                        "load_duration": 0,
                        "cache_read_input_tokens": cache_read,
                        "cache_creation_input_tokens": cache_creation,
                    }
        except _RetryableError as e:
            resp.close()
            if _retries_left <= 0:
                raise RuntimeError(f"Anthropic API: max retries exceeded ({e.message})")
            wait = _RETRY_BACKOFF[min(_MAX_RETRIES - _retries_left, len(_RETRY_BACKOFF) - 1)]
            print(f"  Anthropic overloaded mid-stream, retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
            yield from self._stream(payload, _retries_left=_retries_left - 1)
            return
        finally:
            resp.close()

    def _normalize_response(self, data: dict[str, Any], elapsed_ns: int) -> dict[str, Any]:
        content_parts = []
        tool_calls = []

        for block in data.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "function": {"name": block["name"], "arguments": block.get("input", {})},
                    "id": block.get("id", ""),
                })

        usage = data.get("usage", {})
        result: dict[str, Any] = {
            "message": {
                "content": "\n".join(content_parts),
            },
            "done": True,
            "prompt_eval_count": usage.get("input_tokens", 0),
            "eval_count": usage.get("output_tokens", 0),
            "total_duration": elapsed_ns,
            "prompt_eval_duration": 0,
            "eval_duration": elapsed_ns,
            "load_duration": 0,
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        }
        if tool_calls:
            result["message"]["tool_calls"] = tool_calls
        return result

    def _check_error(self, resp: requests.Response, *, raise_retryable: bool = False) -> None:
        if resp.ok:
            return
        if resp.status_code == 401:
            raise RuntimeError("Anthropic API key is invalid. Check your ANTHROPIC_API_KEY.")
        try:
            err = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err = resp.text
        if resp.status_code in _RETRYABLE_STATUS:
            if raise_retryable:
                raise _RetryableError(resp.status_code, err)
            raise RuntimeError(f"Anthropic API error ({resp.status_code}): {err}")
        raise RuntimeError(f"Anthropic API error ({resp.status_code}): {err}")

    @staticmethod
    def _convert_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """Separate system messages and convert to Anthropic's format."""
        system_parts: list[str] = []
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                system_parts.append(msg.get("content", ""))
            elif role == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": msg.get("tool_use_id", ""), "content": msg.get("content", "")}],
                })
            elif role == "assistant" and msg.get("tool_calls"):
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "input": tc.get("function", {}).get("arguments", {}),
                    })
                api_messages.append({"role": "assistant", "content": content})
            else:
                api_messages.append({"role": role, "content": msg.get("content", "")})

        return "\n\n".join(system_parts), api_messages

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI/Ollama-style tool defs to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            fn = tool.get("function", {})
            anthropic_tools.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools

    def set_model(self, model: str) -> None:
        self.model = model

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = requests.get(
                f"{self._base_url}/v1/models",
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code in (200, 403)
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        return KNOWN_MODELS


class _RetryableError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"Anthropic {status}: {message}")
