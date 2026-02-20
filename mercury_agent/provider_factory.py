"""Factory that creates the right LLM provider from configuration."""

from __future__ import annotations

from .config import Config


def create_provider(cfg: Config):
    """Create an LLM provider instance based on config.provider."""
    provider = cfg.provider.lower()

    if provider == "ollama":
        from .ollama_client import OllamaProvider
        return OllamaProvider(host=cfg.ollama_host, model=cfg.model)

    if provider == "anthropic":
        from .anthropic_client import AnthropicProvider
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for the anthropic provider. Set it in .env or via --api-key.")
        return AnthropicProvider(api_key=cfg.api_key, model=cfg.model, base_url=cfg.api_base_url or "https://api.anthropic.com")

    if provider in ("openai", "openrouter"):
        from .openai_client import OpenAIProvider
        if not cfg.api_key:
            key_name = "OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY"
            raise RuntimeError(f"{key_name} is required for the {provider} provider. Set it in .env or via --api-key.")
        if provider == "openrouter":
            base = cfg.api_base_url or "https://openrouter.ai/api/v1"
            default_model = cfg.model or "anthropic/claude-sonnet-4-20250514"
        else:
            base = cfg.api_base_url or "https://api.openai.com/v1"
            default_model = cfg.model or "gpt-4o"
        return OpenAIProvider(api_key=cfg.api_key, model=default_model, base_url=base)

    raise RuntimeError(f"Unknown provider: {provider}. Use: ollama, anthropic, openai, openrouter")
