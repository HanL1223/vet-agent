"""Runtime settings, read once from environment variables."""

import os
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str
    today: date
    db_path: str

    @property
    def use_claude(self) -> bool:
        return bool(self.anthropic_api_key)


def load_settings() -> Settings:
    today = os.getenv("VETAGENT_TODAY", "")
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("VETAGENT_MODEL", "claude-sonnet-5-5"),
        today=date.fromisoformat(today) if today else date.today(),
        db_path=os.getenv("VETAGENT_DB", "vetagent.db"),
    )
