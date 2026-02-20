"""Abstract LLM provider protocol — all providers implement this interface."""

from __future__ import annotations

from typing import Any, Generator, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Common interface for all LLM providers (Ollama, Anthropic, OpenAI, etc.)."""

    model: str
    history: list[dict[str, Any]]

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
        """Send a chat request. Returns a response dict (blocking) or generator of chunks (streaming).

        All providers normalize their output to a common chunk format:
        {
            "message": {
                "content": "...",           # text token (streaming) or full text (blocking)
                "tool_calls": [...]  | None # tool calls if any
            },
            "done": bool,                   # True on final chunk / blocking response
            # Optional Ollama-style metrics (providers that don't have them return 0):
            "prompt_eval_count": int,
            "eval_count": int,
            "prompt_eval_duration": int,    # nanoseconds
            "eval_duration": int,           # nanoseconds
            "total_duration": int,          # nanoseconds
        }
        """
        ...

    def supports_tools(self) -> bool:
        """Whether the current model supports tool-calling."""
        ...

    def is_available(self) -> bool:
        """Check if the provider is reachable."""
        ...

    def list_models(self) -> list[str]:
        """List available models."""
        ...

    def set_model(self, model: str) -> None:
        """Switch to a different model."""
        ...

    def add_message(self, role: str, content: str) -> None:
        ...

    def add_tool_call(self, tool_calls: list[dict]) -> None:
        ...

    def add_tool_result(self, content: str, tool_use_id: str = "") -> None:
        ...

    def trim_history(self, max_tokens: int) -> None:
        ...

    def clear_history(self) -> None:
        ...


class BaseProvider:
    """Shared conversation-history logic for all providers."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.history: list[dict[str, Any]] = []

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def add_tool_call(self, tool_calls: list[dict]) -> None:
        self.history.append({"role": "assistant", "tool_calls": tool_calls})

    def add_tool_result(self, content: str, tool_use_id: str = "") -> None:
        self.history.append({"role": "tool", "content": content, "tool_use_id": tool_use_id})

    def trim_history(self, max_tokens: int) -> None:
        while self._estimate_tokens() > max_tokens and len(self.history) > 1:
            self.history.pop(0)

    def clear_history(self) -> None:
        self.history.clear()

    def _estimate_tokens(self) -> int:
        total = 0
        for msg in self.history:
            total += len(msg.get("content", "")) // 4
        return total
