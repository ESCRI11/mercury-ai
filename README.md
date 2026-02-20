# Mercury AI

LLM-powered orchestrator for [Mercury Playground](https://github.com/tmhglnd/mercury-playground) live coding. Talk to an LLM and it writes music and visuals for you in real time.

## Features

- **Multi-provider**: Ollama (local), Anthropic (Claude), OpenAI, OpenRouter
- **Tool calling**: LLM sends code directly to Mercury via `send_code`, `silence`, `get_current_piece`
- **Live sync**: Edits you make in Mercury Playground are picked up by the agent
- **CLI + Web UI**: Terminal-based Rich CLI or browser-based chat interface
- **Hydra visuals**: Web UI renders live Hydra visuals from the current piece
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

## Mercury Playground patches

This agent requires two small patches to Mercury Playground's `server.js` and `src/editor.js` for live code sync (`GET /api/code` endpoint + evaluate-emit). See the [mercury-playground fork](https://github.com/ESCRI11/mercury-playground) for details.
