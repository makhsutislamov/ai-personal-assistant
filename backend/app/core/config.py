from __future__ import annotations

import os
import stat
from pathlib import Path

import platformdirs

from app.models.schemas import SettingsSchema

_APP_NAME = "ai-personal-assistant"
_SETTINGS_FILE = "settings.json"


class ConfigManager:
    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is not None:
            self._config_dir = config_dir
        else:
            self._config_dir = Path(platformdirs.user_config_dir(_APP_NAME))

    def get_settings_path(self) -> Path:
        return self._config_dir / _SETTINGS_FILE

    def load(self) -> SettingsSchema:
        path = self.get_settings_path()
        if not path.exists():
            return SettingsSchema()
        try:
            return SettingsSchema.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            return SettingsSchema()

    def save(self, settings: SettingsSchema) -> None:
        path = self.get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        # Restrict permissions to owner-only (rw-------)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
