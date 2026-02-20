"""OpenAI-compatible API provider — works with OpenAI, OpenRouter, and any compatible endpoint."""

from __future__ import annotations

import json
import time
from typing import Any, Generator

import requests

from .provider import BaseProvider

OPENAI_API_URL = "https://api.openai.com/v1"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = OPENAI_API_URL) -> None:
        super().__init__(model)
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        if "openrouter" in self._base_url:
            return "openrouter"
        return "openai"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def supports_tools(self) -> bool:
        return True

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
        api_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if stream:
            return self._stream(payload)
        return self._blocking(payload)

    def _blocking(self, payload: dict[str, Any]) -> dict[str, Any]:
        t0 = time.time()
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=(10, 300),
        )
        elapsed_ns = int((time.time() - t0) * 1_000_000_000)
        self._check_error(resp)
        data = resp.json()
        return self._normalize_response(data, elapsed_ns)

    def _stream(self, payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        t0 = time.time()
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=(10, 300),
        )
        self._check_error(resp)

        output_tokens = 0
        input_tokens = 0
        tool_calls_buf: dict[int, dict[str, Any]] = {}

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
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue

            usage = chunk.get("usage")
            if usage:
                input_tokens = usage.get("prompt_tokens", input_tokens)
                output_tokens = usage.get("completion_tokens", output_tokens)

            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})

            # Text content
            content = delta.get("content")
            if content:
                yield {"message": {"content": content}, "done": False}

            # Tool calls (streamed incrementally)
            for tc_delta in delta.get("tool_calls", []):
                idx = tc_delta.get("index", 0)
                if idx not in tool_calls_buf:
                    tool_calls_buf[idx] = {
                        "id": tc_delta.get("id", ""),
                        "name": "",
                        "arguments": "",
                    }
                fn = tc_delta.get("function", {})
                if fn.get("name"):
                    tool_calls_buf[idx]["name"] = fn["name"]
                if fn.get("arguments"):
                    tool_calls_buf[idx]["arguments"] += fn["arguments"]

            # Check for finish
            finish = choices[0].get("finish_reason")
            if finish:
                # Emit accumulated tool calls
                if tool_calls_buf:
                    tc_list = []
                    for _, buf in sorted(tool_calls_buf.items()):
                        try:
                            args = json.loads(buf["arguments"]) if buf["arguments"] else {}
                        except json.JSONDecodeError:
                            args = {}
                        tc_list.append({
                            "function": {"name": buf["name"], "arguments": args},
                            "id": buf["id"],
                        })
                    yield {"message": {"content": "", "tool_calls": tc_list}, "done": False}
                    tool_calls_buf.clear()

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
                }

    def _normalize_response(self, data: dict[str, Any], elapsed_ns: int) -> dict[str, Any]:
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        result: dict[str, Any] = {
            "message": {
                "content": msg.get("content", "") or "",
            },
            "done": True,
        }

        # Tool calls
        if msg.get("tool_calls"):
            tc_list = []
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                tc_list.append({
                    "function": {"name": fn.get("name", ""), "arguments": args},
                    "id": tc.get("id", ""),
                })
            result["message"]["tool_calls"] = tc_list

        usage = data.get("usage", {})
        result.update({
            "prompt_eval_count": usage.get("prompt_tokens", 0),
            "eval_count": usage.get("completion_tokens", 0),
            "total_duration": elapsed_ns,
            "prompt_eval_duration": 0,
            "eval_duration": elapsed_ns,
            "load_duration": 0,
        })
        return result

    def _check_error(self, resp: requests.Response) -> None:
        if resp.status_code == 401:
            raise RuntimeError(f"{self.provider_name} API key is invalid. Check your API key.")
        if resp.status_code == 429:
            raise RuntimeError(f"{self.provider_name} rate limit exceeded. Wait and try again.")
        if not resp.ok:
            try:
                err = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err = resp.text
            raise RuntimeError(f"{self.provider_name} API error ({resp.status_code}): {err}")

    @staticmethod
    def _convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert to OpenAI chat format (tool results use 'tool' role)."""
        api_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant" and msg.get("tool_calls"):
                tc_formatted = []
                for tc in msg["tool_calls"]:
                    tc_formatted.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": json.dumps(tc.get("function", {}).get("arguments", {})),
                        },
                    })
                entry: dict[str, Any] = {"role": "assistant", "tool_calls": tc_formatted}
                if msg.get("content"):
                    entry["content"] = msg["content"]
                api_messages.append(entry)
            elif role == "tool":
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": msg.get("content", ""),
                })
            else:
                api_messages.append({"role": role, "content": msg.get("content", "")})
        return api_messages

    def set_model(self, model: str) -> None:
        self.model = model

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = requests.get(
                f"{self._base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(
                f"{self._base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                return sorted([m["id"] for m in data.get("data", [])])
        except requests.RequestException:
            pass
        return []
