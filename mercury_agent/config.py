"""Environment-based configuration with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


_MODEL_DEFAULTS = {
    "ollama": "llama3",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "openrouter": "anthropic/claude-sonnet-4-20250514",
}

_CONTEXT_DEFAULTS = {
    "ollama": 8192,
    "anthropic": 200000,
    "openai": 128000,
    "openrouter": 128000,
}


@dataclass
class Config:
    # Provider: ollama | anthropic | openai | openrouter
    provider: str = field(default_factory=lambda: _env("PROVIDER", "ollama"))

    # Model name (if empty, a sensible default is chosen per provider)
    model: str = field(default_factory=lambda: _env("MODEL", ""))

    # API key (used by anthropic, openai, openrouter)
    api_key: str = field(default_factory=lambda: (
        _env("API_KEY")
        or _env("ANTHROPIC_API_KEY")
        or _env("OPENAI_API_KEY")
        or _env("OPENROUTER_API_KEY")
    ))

    # Optional custom base URL (overrides provider default)
    api_base_url: str = field(default_factory=lambda: _env("API_BASE_URL", ""))

    # Ollama-specific
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))

    # Mercury Playground
    mercury_url: str = field(default_factory=lambda: _env("MERCURY_URL", "http://localhost:8080"))
    context_window: int = field(default_factory=lambda: int(_env("CONTEXT_WINDOW", "8192")))

    mercury_playground_dir: Path = field(
        default_factory=lambda: Path(_env("MERCURY_PLAYGROUND_DIR", str(Path.home() / "mercury-playground"))).expanduser()
    )

    def __post_init__(self) -> None:
        if not self.model:
            self.model = _MODEL_DEFAULTS.get(self.provider.lower(), "llama3")
        if not _env("CONTEXT_WINDOW"):
            self.context_window = _CONTEXT_DEFAULTS.get(self.provider.lower(), 8192)

    @property
    def state_file(self) -> Path:
        return self.mercury_playground_dir / "current_piece.txt"

    @property
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def compose_skill(self) -> Path:
        return self._repo_root / "skills" / "mercury-compose.md"

    @property
    def kokoro_skill(self) -> Path:
        return self._repo_root / "skills" / "mercury-kokoro.md"


def load_config(**overrides) -> Config:
    """Create a Config, optionally overriding fields."""
    cfg = Config()
    for k, v in overrides.items():
        if v is not None and hasattr(cfg, k):
            setattr(cfg, k, v)
    cfg.__post_init__()
    return cfg
