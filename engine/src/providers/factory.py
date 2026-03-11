from engine.src.config import EmbeddingConfig
from engine.src.providers.base import EmbeddingProvider


def create_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """
    Factory: instantiate the correct EmbeddingProvider from config.

    config: EmbeddingConfig — Provider configuration with provider field.
    Returns: EmbeddingProvider — Concrete provider instance.
    Raises: ValueError — If provider type is unknown.
    """
    if config.provider == "fastembed":
        from engine.src.providers.fastembed_provider import FastEmbedProvider
        return FastEmbedProvider(config)

    if config.provider == "litellm":
        from engine.src.providers.litellm_provider import LiteLLMProvider
        return LiteLLMProvider(config)

    raise ValueError(
        f"Unknown embedding provider: {config.provider!r}. "
        f"Supported: 'fastembed', 'litellm'"
    )
