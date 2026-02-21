# Mercury AI

LLM-powered orchestrator for [Mercury Playground](https://github.com/tmhglnd/mercury-playground) live coding. Talk to an LLM and it writes music and visuals for you in real time.

## Features

- **Multi-provider**: Ollama (local), Anthropic (Claude), OpenAI, OpenRouter
- **Tool calling**: LLM sends code directly to Mercury via `send_code`, `silence`, `get_current_piece`
- **Live sync**: Edits you make in Mercury Playground are picked up by the agent
- **CLI + Web UI**: Terminal-based Rich CLI or browser-based chat interface
- **Embedded in Playground**: Chat panel integrates directly into Mercury Playground as a collapsible right column — Hydra visuals stay as the shared immersive background
- **Prompt caching**: Anthropic cache headers reduce cost on repeated calls

## Prerequisites

- [Mercury Playground](https://github.com/tmhglnd/mercury-playground) running on `http://localhost:8080`
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- One of: local [Ollama](https://ollama.ai/) instance, Anthropic API key, OpenAI API key, or OpenRouter API key

## Setup

```bash
cp .env.example .env
# Edit .env — set your provider and API key
```

## Usage

```bash
# CLI (default: Ollama)
uv run mercury-cli

# CLI with Anthropic
uv run mercury-cli --provider anthropic

# Web UI on port 3000
uv run mercury-web --port 3000

# Web UI with a specific provider
uv run mercury-web --provider anthropic --port 3000
```

### CLI commands

| Command | Description |
|---------|-------------|
| `/play` | Resume the last piece after silence |
| `/silence` | Stop all sound |
| `/model <name>` | Switch model |
| `/models` | List available models |
| `/status` | Show current status |
| `/clear` | Clear conversation history |
| `/help` | Show all commands |
| `/quit` | Exit |

## Embedded chat in Mercury Playground

The AI chat panel is embedded directly into Mercury Playground's frontend (`public/index.html`). When you click the **AI** button, a collapsible panel slides in from the right. The Hydra canvas remains as the full-screen background — chat text uses per-line highlights (matching CodeMirror's style) so visuals bleed through between lines.

The panel connects to the Mercury AI backend via WebSocket (`ws://localhost:3000/ws` by default). Override the URL with `localStorage.setItem('mercury-ai-url', 'ws://your-host:port/ws')`.

**How to use it:**

1. Start Mercury Playground on port 8080
2. Start the Mercury AI backend: `uv run mercury-web --port 3000`
3. Open Mercury Playground in your browser, click the **AI** button on the right edge
4. Type what you want and the LLM writes music + visuals in real time

The styling uses Mercury's own CSS variables (`--button-bg`, `--accent`, `--cm-line`, etc.) so it adapts to dark, light, and color themes automatically.

## Mercury Playground patches

This agent requires patches to Mercury Playground's `server.js`, `src/editor.js`, and `public/index.html` (embedded chat panel). See the [mercury-playground fork](https://github.com/ESCRI11/mercury-playground) on the `feat/kokoro-tts` branch for the full set of changes.
