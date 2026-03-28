from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class WebSettings(BaseModel):
    default_days: int = Field(default=30, ge=1, le=180)


class SettingsStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load(self) -> WebSettings:
        if not self.file_path.exists():
            settings = WebSettings()
            self.save(settings)
            return settings

        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            settings = WebSettings()
            self.save(settings)
            return settings

        merged = {
            "default_days": raw.get("default_days", 30),
        }

        try:
            settings = WebSettings(**merged)
        except ValidationError:
            settings = WebSettings()

        self.save(settings)
        return settings

    def save(self, settings: WebSettings) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            settings.model_dump_json(indent=2),
            encoding="utf-8",
        )
