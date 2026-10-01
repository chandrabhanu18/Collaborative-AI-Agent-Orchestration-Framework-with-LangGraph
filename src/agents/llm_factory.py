"""
LLM Factory for instantiating LangChain chat models or fallback synthesizers.
"""
import logging
from typing import Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_llm():
    """
    Returns a LangChain BaseChatModel if a valid API key is present.
    Returns None if running with placeholder or mock keys.
    """
    api_key = settings.LLM_API_KEY
    if not api_key or api_key.startswith("sk-your") or api_key == "dummy":
        return None

    provider = settings.LLM_PROVIDER.lower()
    try:
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.LLM_MODEL or "gpt-4o-mini",
                api_key=api_key,
                temperature=settings.LLM_TEMPERATURE,
            )
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.LLM_MODEL or "claude-3-haiku-20240307",
                anthropic_api_key=api_key,
                temperature=settings.LLM_TEMPERATURE,
            )
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.LLM_MODEL or "gpt-4o-mini",
                api_key=api_key,
                temperature=settings.LLM_TEMPERATURE,
            )
    except Exception as e:
        logger.warning(f"Could not initialize {provider} LLM ({e}). Falling back to internal engine.")
        return None
