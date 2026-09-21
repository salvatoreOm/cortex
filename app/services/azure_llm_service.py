from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings


class AzureConfigError(Exception):
    """Raised when required Azure AI Foundry settings are missing from .env."""


@lru_cache
def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.azure_ai_endpoint or not settings.azure_ai_key:
        raise AzureConfigError("AZURE_AI_ENDPOINT and AZURE_AI_KEY must be set in .env")
    return AsyncOpenAI(api_key=settings.azure_ai_key, base_url=settings.azure_ai_endpoint)


async def get_embedding(text: str) -> list[float]:
    """Embed one piece of text using the configured Azure embedding deployment."""
    settings = get_settings()
    if not settings.azure_embedding_deployment:
        raise AzureConfigError("AZURE_EMBEDDING_DEPLOYMENT must be set in .env")

    response = await _get_client().embeddings.create(
        model=settings.azure_embedding_deployment, input=text
    )
    return response.data[0].embedding


async def get_chat_completion(messages: list[dict[str, str]]) -> str:
    """Get a chat completion from the configured Azure chat deployment. Used in Phase 3."""
    settings = get_settings()
    if not settings.azure_chat_deployment:
        raise AzureConfigError("AZURE_CHAT_DEPLOYMENT must be set in .env")

    response = await _get_client().chat.completions.create(
        model=settings.azure_chat_deployment, messages=messages
    )
    return response.choices[0].message.content or ""
