"""
Application configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for the chatbot application."""

    # ----- LLM Provider Keys -----
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # ----- MySQL Database -----
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "chatbot_db")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))

    # ----- Flask -----
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # ----- Defaults -----
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_OPENAI_MODEL: str = "gpt-4o"
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_MESSAGES_BEFORE_SUMMARY: int = 5
    MESSAGES_TO_KEEP_AFTER_SUMMARY: int = 5
