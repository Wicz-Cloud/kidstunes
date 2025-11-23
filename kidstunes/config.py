from pathlib import Path
from typing import Any, Optional, cast

import yaml


class Config:
    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(self.config_path, "r") as f:
            self.data = yaml.safe_load(f)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def discord_token(self) -> str:
        return cast(str, self.get("discord.token"))

    @property
    def request_channel_id(self) -> int:
        return cast(int, self.get("discord.request_channel_id"))

    @property
    def approval_channel_id(self) -> int:
        return cast(int, self.get("discord.approval_channel_id"))

    @property
    def admin_role_id(self) -> int:
        return cast(int, self.get("discord.admin_role_id"))

    @property
    def output_dir(self) -> str:
        return cast(str, self.get("paths.output_dir"))

    @property
    def database_path(self) -> str:
        return cast(str, self.get("paths.database"))

    @property
    def temp_dir(self) -> str:
        return cast(str, self.get("paths.temp_dir"))

    @property
    def audio_format(self) -> str:
        return cast(str, self.get("ytdlp.audio_format"))

    @property
    def audio_quality(self) -> str:
        return cast(str, self.get("ytdlp.audio_quality"))

    @property
    def search_prefix(self) -> str:
        return cast(str, self.get("ytdlp.search_prefix"))

    @property
    def xai_api_key(self) -> str:
        return cast(str, self.get("xai.api_key"))

    @property
    def xai_model(self) -> str:
        return cast(str, self.get("xai.model"))

    @property
    def beets_enabled(self) -> bool:
        return cast(bool, self.get("beets.enabled", False))

    @property
    def beets_library_path(self) -> str:
        return cast(str, self.get("beets.library_path", "/tmp/beets_library.db"))

    @property
    def beets_music_directory(self) -> str:
        return cast(str, self.get("beets.music_directory", self.output_dir))

    @property
    def beets_import_config(self) -> dict:
        return cast(dict, self.get("beets.import_config", {}))
