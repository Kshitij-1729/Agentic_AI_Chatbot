"""
LLM provider factory — returns a ChatModel based on provider name.
Supports OpenAI and Google Gemini through their official LangChain packages.
"""

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from config import Config


# Available models per provider
PROVIDER_MODELS = {
    "openai": {
        "default": Config.DEFAULT_OPENAI_MODEL,
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
    },
    "gemini": {
        "default": Config.DEFAULT_GEMINI_MODEL,
        "models": [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ],
    },
}


def get_llm(provider: str = "openai", model: str = None, temperature: float = 0.7):
    """
    Factory that returns the appropriate LangChain chat model.

    Args:
        provider: 'openai' or 'gemini'
        model:    specific model name (uses provider default if None)
        temperature: sampling temperature

    Returns:
        A LangChain BaseChatModel instance
    """
    provider = provider.lower().strip()

    if provider == "openai":
        model_name = model or PROVIDER_MODELS["openai"]["default"]
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=Config.OPENAI_API_KEY,
            streaming=True,
        )
    elif provider == "gemini":
        model_name = model or PROVIDER_MODELS["gemini"]["default"]
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=Config.GOOGLE_API_KEY,
            convert_system_message_to_human=True,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: '{provider}'. Use 'openai' or 'gemini'.")


def list_providers() -> dict:
    """Return available providers and their models for the frontend dropdown."""
    return PROVIDER_MODELS
