"""Tool definitions for Ollama tool-calling and dispatch logic."""

from __future__ import annotations

from typing import Any

from .mercury_client import MercuryClient
from .state import PieceState

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "send_code",
            "description": "Evaluate Mercury live-coding language in the browser. Sends the full Mercury code to the running Mercury Playground webapp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Complete Mercury code to evaluate",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "silence",
            "description": "Stop all sound in Mercury Playground.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_piece",
            "description": "Retrieve the Mercury code that is currently playing (includes changes made in the browser editor).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


class ToolDispatcher:
    """Execute tool calls returned by the model and produce results."""

    def __init__(self, mercury: MercuryClient, state: PieceState) -> None:
        self._mercury = mercury
        self._state = state
        self.last_code_sent: str | None = None

    def dispatch(self, tool_call: dict[str, Any]) -> str:
        fn = tool_call.get("function", {})
        name = fn.get("name", "")
        args = fn.get("arguments", {})

        if name == "send_code":
            code = args.get("code", "")
            if code:
                self._mercury.send_code(code)
                self._state.write(code)
                self.last_code_sent = code
                return f"Code sent to Mercury ({len(code.splitlines())} lines)."
            return "Error: no code provided."

        if name == "silence":
            self._mercury.silence()
            self._state.clear()
            self.last_code_sent = None
            return "Silenced."

        if name == "get_current_piece":
            live = self._mercury.get_current_code()
            if live:
                self._state.write(live)
                return live
            piece = self._state.read()
            if piece:
                return piece
            return "(No piece currently playing.)"

        return f"Unknown tool: {name}"
