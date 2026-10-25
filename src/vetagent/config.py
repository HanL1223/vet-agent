"""Runtime settings, read once from environment variables."""

import os
from dataclasses import dataclass
from datetime import date

PROVIDERS = ("anthropic", "openai")
DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-5"}


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str
    today: date
    db_path: str
    provider: str = "anthropic"
    openai_api_key: str = ""

    @property
    def api_key(self) -> str:
        """Key for the chosen provider; empty means run offline with the scripted model."""
        return self.openai_api_key if self.provider == "openai" else self.anthropic_api_key


def load_settings() -> Settings:
    today = os.getenv("VETAGENT_TODAY", "")
    provider = os.getenv("VETAGENT_PROVIDER", "anthropic").strip().lower() or "anthropic"
    if provider not in PROVIDERS:
        raise ValueError(f"VETAGENT_PROVIDER must be one of {PROVIDERS}, got {provider!r}")
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("VETAGENT_MODEL", "") or DEFAULT_MODELS[provider],
        today=date.fromisoformat(today) if today else date.today(),
        db_path=os.getenv("VETAGENT_DB", "vetagent.db"),
        provider=provider,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
    )
