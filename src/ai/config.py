"""
CloudSense AI — AI Copilot Configuration
Manages Gemini model settings, API credentials, and execution modes.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIConfig(BaseSettings):
    # Gemini API Credentials (read from environment, NEVER hardcoded)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("CLOUDSENSE_GEMINI_API_KEY", ""))
    gemini_model: str = os.getenv("CLOUDSENSE_GEMINI_MODEL", "gemini-2.0-flash")
    temperature: float = 0.1  # Low temperature for strict factual fidelity
    max_output_tokens: int = 1500

    # Fallback to local grounded simulation if no API key is provided
    mock_mode: bool = os.getenv("CLOUDSENSE_AI_MOCK_MODE", "").lower() in ("true", "1")

    model_config = SettingsConfigDict(env_prefix="CLOUDSENSE_AI_", case_sensitive=False)


ai_config = AIConfig()
