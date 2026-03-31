"""LLM factory — returns a LangChain chat model based on environment config.

Priority:
1. OLLAMA_MODEL env var -> use langchain-ollama (free, local)
2. OPENAI_API_KEY env var -> use ChatOpenAI
3. Raise a clear error explaining setup options.
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel


def get_llm(**kwargs: Any) -> BaseChatModel:
    """Return a configured LangChain chat model.

    Keyword arguments are forwarded to the underlying model constructor,
    allowing callers to override ``temperature``, ``max_tokens``, etc.

    Returns:
        A LangChain ``BaseChatModel`` instance.

    Raises:
        RuntimeError: If neither Ollama nor OpenAI is configured.
    """

    ollama_model = os.getenv("OLLAMA_MODEL")
    openai_key = os.getenv("OPENAI_API_KEY")

    if ollama_model:
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise ImportError(
                "langchain-ollama is required when OLLAMA_MODEL is set. "
                "Install it with: pip install langchain-ollama"
            ) from exc

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        defaults = {"model": ollama_model, "base_url": base_url, "temperature": 0}
        defaults.update(kwargs)
        return ChatOllama(**defaults)

    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required when OPENAI_API_KEY is set. "
                "Install it with: pip install langchain-openai"
            ) from exc

        defaults = {"api_key": openai_key, "model": "gpt-4o-mini", "temperature": 0}
        defaults.update(kwargs)
        return ChatOpenAI(**defaults)

    raise RuntimeError(
        "No LLM configured. Set one of the following environment variables:\n"
        "  * OLLAMA_MODEL  (e.g. llama3.2) -- free, local via Ollama\n"
        "  * OPENAI_API_KEY -- requires an OpenAI account\n\n"
        "See .env.example for details."
    )
