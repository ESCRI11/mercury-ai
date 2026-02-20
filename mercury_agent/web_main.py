#!/usr/bin/env python3
"""Entry point for the Mercury × LLM Web UI."""

import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from .config import load_config
from .web import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Mercury × LLM Web UI")
    parser.add_argument("--provider", help="LLM provider: ollama, anthropic, openai, openrouter")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--api-key", help="API key (for anthropic/openai/openrouter)")
    parser.add_argument("--api-base-url", help="Custom API base URL")
    parser.add_argument("--ollama-host", help="Ollama API base URL")
    parser.add_argument("--mercury-url", help="Mercury Playground base URL")
    parser.add_argument("--context-window", type=int, help="Context window size in tokens")
    parser.add_argument("--host", default="0.0.0.0", help="Web server bind host")
    parser.add_argument("--port", type=int, default=3000, help="Web server port")
    args = parser.parse_args()

    overrides = {}
    if args.provider:
        overrides["provider"] = args.provider
    if args.model:
        overrides["model"] = args.model
    if args.api_key:
        overrides["api_key"] = args.api_key
    if args.api_base_url:
        overrides["api_base_url"] = args.api_base_url
    if args.ollama_host:
        overrides["ollama_host"] = args.ollama_host
    if args.mercury_url:
        overrides["mercury_url"] = args.mercury_url
    if args.context_window:
        overrides["context_window"] = args.context_window

    cfg = load_config(**overrides)
    app = create_app(cfg)

    import uvicorn
    provider_name = cfg.provider
    print(f"\nMercury × LLM Web UI")
    print(f"  → http://{args.host}:{args.port}")
    print(f"  Provider: {provider_name}")
    print(f"  Model: {cfg.model}")
    print(f"  Mercury: {cfg.mercury_url}\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
