"""Extract Mercury code from LLM text responses (fallback when tool-calling is unavailable)."""

from __future__ import annotations

import re

# Match any fenced code block: ```<optional-lang>\n...\n```
_FENCE_RE = re.compile(r"```\w*\s*\n(.*?)```", re.DOTALL)

_MERCURY_MARKERS = ("set tempo", "new sample", "new synth", "new kokoro", "new poly", "new loop", "new noise", "silence")


def looks_like_mercury(text: str) -> bool:
    lower = text.lower()
    return any(m in lower for m in _MERCURY_MARKERS)


def extract_code(response: str) -> str | None:
    """Return Mercury code extracted from the LLM response, or None if conversational."""
    blocks = _FENCE_RE.findall(response)
    if blocks:
        # Prefer blocks that look like Mercury code
        for block in reversed(blocks):
            code = block.strip()
            if looks_like_mercury(code):
                return code
        # No block matched Mercury heuristics — don't send random code
        return None

    # No fenced block — check if the whole response looks like Mercury code
    stripped = response.strip()
    if looks_like_mercury(stripped) and len(stripped.splitlines()) >= 2:
        return stripped

    return None
