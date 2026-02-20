"""Parse and format Ollama response performance metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ResponseMetrics:
    prompt_tokens: int = 0
    generated_tokens: int = 0
    prompt_eval_ms: float = 0
    eval_ms: float = 0
    total_ms: float = 0
    load_ms: float = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def prompt_tok_per_sec(self) -> float:
        if self.prompt_eval_ms <= 0:
            return 0
        return self.prompt_tokens / (self.prompt_eval_ms / 1000)

    @property
    def gen_tok_per_sec(self) -> float:
        if self.eval_ms <= 0:
            return 0
        return self.generated_tokens / (self.eval_ms / 1000)

    def format_compact(self) -> str:
        parts = []
        if self.prompt_tokens:
            parts.append(f"prompt: {self.prompt_tokens} tok")
            if self.prompt_tok_per_sec:
                parts[-1] += f" @ {self.prompt_tok_per_sec:.1f} t/s"
        if self.cache_read_tokens:
            parts.append(f"cached: {self.cache_read_tokens} tok")
        if self.generated_tokens:
            parts.append(f"gen: {self.generated_tokens} tok @ {self.gen_tok_per_sec:.1f} t/s")
        if self.total_ms:
            parts.append(f"total: {self.total_ms / 1000:.1f}s")
        return " · ".join(parts) if parts else "no metrics"

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "generated_tokens": self.generated_tokens,
            "prompt_tok_per_sec": round(self.prompt_tok_per_sec, 1),
            "gen_tok_per_sec": round(self.gen_tok_per_sec, 1),
            "total_ms": round(self.total_ms),
            "load_ms": round(self.load_ms),
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
        }


def extract_metrics(data: dict[str, Any]) -> ResponseMetrics:
    def ns_to_ms(ns: int | float) -> float:
        return ns / 1_000_000

    return ResponseMetrics(
        prompt_tokens=data.get("prompt_eval_count", 0),
        generated_tokens=data.get("eval_count", 0),
        prompt_eval_ms=ns_to_ms(data.get("prompt_eval_duration", 0)),
        eval_ms=ns_to_ms(data.get("eval_duration", 0)),
        total_ms=ns_to_ms(data.get("total_duration", 0)),
        load_ms=ns_to_ms(data.get("load_duration", 0)),
        cache_read_tokens=data.get("cache_read_input_tokens", 0),
        cache_creation_tokens=data.get("cache_creation_input_tokens", 0),
    )
