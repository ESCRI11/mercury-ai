"""Single source of truth for the currently playing Mercury piece."""

from __future__ import annotations

from pathlib import Path


class PieceState:
    def __init__(self, state_file: Path) -> None:
        self._path = state_file

    def read(self) -> str:
        """Return the current piece, or empty string if none."""
        if self._path.exists():
            return self._path.read_text(encoding="utf-8").strip()
        return ""

    def write(self, code: str) -> None:
        """Persist the current piece to disk."""
        self._path.write_text(code + "\n", encoding="utf-8")

    def clear(self) -> None:
        self.write("")
