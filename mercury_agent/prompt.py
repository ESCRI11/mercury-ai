"""Build the system prompt from SKILL.md files, trimmed to fit the model's context window."""

from __future__ import annotations

import re
from pathlib import Path

from .config import Config

ORCHESTRATOR_PREAMBLE = """\
You are a Mercury live-coding composer. You control a running Mercury Playground \
webapp by writing Mercury code.

RULES:
- Respond ONLY with Mercury code inside a ```mercury fenced code block. \
Do NOT explain what you did, why, or how. No commentary, no bullet points, \
no summaries. Just the code.
- When evolving an existing piece, make 3-4 targeted changes rather than \
rewriting everything.
- If you have access to the `send_code` tool, call it to send code to Mercury. \
Otherwise just include the code in your response and it will be sent automatically.
- To stop all sound, either call the `silence` tool or output the single word \
`silence` in a code block.
- You can compose with the Kokoro TTS voice instrument (`new kokoro`).
- Always include `set tempo <bpm>` at the top of new pieces.

CRITICAL MERCURY SYNTAX — lists must be SINGLE-LINE, SPACE-separated, NO commas:
  CORRECT: list vis ['osc(8,0.1,1).color(0.3,0.5,0.9).out()' 'noise(3).color(0.2,0.1,0.3).out()']
  WRONG:   list vis [
             'osc(8,0.1,1).color(0.3,0.5,0.9).out()',
             'noise(3).color(0.2,0.1,0.3).out()'
           ]
Commas INSIDE Hydra function arguments (e.g. osc(8,0.1,1)) are correct. \
Commas BETWEEN list items are WRONG — use spaces only. \
Multi-line lists are WRONG — everything on ONE line after `list <name>`.
Hydra visual strings must be short (max 4-5 chained calls). \
Avoid nesting source functions inside modulate/blend arguments.
"""

# Sections in SKILL.md files ordered by priority (keep top ones, cut bottom ones)
_SECTION_PRIORITY = [
    "Quick Reference",
    "Core Parameters",
    "Mercury Language Reference",
    "Global Settings",
    "Instruments",
    "Core Methods",
    "Effects",
    "Lists",
    "Hydra Visuals Integration",
    "Available Sounds",
    "Composition Tips",
    "Complete Examples",
    "Hydra Visual Recipes",
]


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _trim_skill(text: str, budget_chars: int) -> str:
    """Remove lower-priority sections to fit within budget."""
    if len(text) <= budget_chars:
        return text

    lines = text.splitlines()
    # Find section boundaries (## or ### headings)
    sections: list[tuple[str, int, int]] = []
    current_heading = "__top__"
    current_start = 0
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s+", line):
            sections.append((current_heading, current_start, i))
            current_heading = line.lstrip("#").strip()
            current_start = i
    sections.append((current_heading, current_start, len(lines)))

    # Score sections by priority (lower index = higher priority)
    def section_priority(name: str) -> int:
        for idx, keyword in enumerate(_SECTION_PRIORITY):
            if keyword.lower() in name.lower():
                return idx
        return len(_SECTION_PRIORITY) + 1

    # Sort sections by priority (keep high priority first when cutting)
    scored = [(section_priority(name), name, start, end) for name, start, end in sections]
    scored.sort(key=lambda x: x[0])

    result_lines: list[str] = []
    char_count = 0
    # Re-assemble in original order, but only include sections that fit
    included_ranges: list[tuple[int, int]] = []
    for _, _, start, end in scored:
        section_text = "\n".join(lines[start:end])
        if char_count + len(section_text) <= budget_chars:
            included_ranges.append((start, end))
            char_count += len(section_text)

    # Output in original document order
    included_ranges.sort()
    for start, end in included_ranges:
        result_lines.extend(lines[start:end])

    return "\n".join(result_lines)


def build_system_prompt(cfg: Config) -> str:
    """Load skills and build the full system prompt, trimmed to context budget."""
    parts: list[str] = [ORCHESTRATOR_PREAMBLE]

    budget_chars = cfg.context_window * 4  # rough: 1 token ~= 4 chars
    # Reserve ~25% of context for conversation history
    skill_budget = int(budget_chars * 0.75) - len(ORCHESTRATOR_PREAMBLE)

    skill_paths = [cfg.compose_skill, cfg.kokoro_skill, cfg.hydra_skill, cfg.hydra_reference_skill]
    per_skill_budget = skill_budget // len(skill_paths)
    for skill_path in skill_paths:
        if skill_path.exists():
            raw = skill_path.read_text(encoding="utf-8")
            # Strip YAML front-matter
            raw = re.sub(r"^---\n.*?---\n", "", raw, count=1, flags=re.DOTALL)
            trimmed = _trim_skill(raw, per_skill_budget)
            parts.append(trimmed.strip())
        else:
            parts.append(f"(Skill file not found: {skill_path})")

    prompt = "\n\n---\n\n".join(parts)

    # Final safety trim
    if _estimate_tokens(prompt) > cfg.context_window:
        prompt = prompt[: cfg.context_window * 4]

    return prompt


def save_prompt(prompt: str, output_path: Path) -> None:
    """Save the generated prompt for inspection."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt, encoding="utf-8")
