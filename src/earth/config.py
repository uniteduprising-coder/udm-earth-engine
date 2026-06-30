from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8790
    cors_origins: str = (
        "http://localhost:5173,http://localhost:8790,http://127.0.0.1:8790,"
        "https://uniteduprising.com,https://www.uniteduprising.com,"
        "https://earth.uniteduprising.com"
    )

    nasa_api_key: str = ""
    nasa_epic_base: str = "https://api.nasa.gov/EPIC/api"
    geo_stream_base: str = "https://geo-api.uniteduprising.com"
    geo_stream_local: str = "http://127.0.0.1:8789"

    webhook_secret: str = "change-me-in-production"
    cache_dir: str = "data/cache"
    kml_enriched_path: str = (
        r"C:\Users\User\Downloads\United-Uprising-WS-Code\vesper-knowledge\requested-data\kml-sites-enriched.json"
    )
    forensic_kml_path: str = (
        r"C:\Users\User\Downloads\archives\Requested Data\Requested Data\Mysterious Sites.kml"
    )
    seed_dir: str = "data/seed"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cache_path(self) -> Path:
        p = ROOT / self.cache_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def seed_path(self) -> Path:
        return ROOT / self.seed_dir

    def load_feeds(self) -> list[dict]:
        return json.loads((ROOT / "config" / "feeds.json").read_text(encoding="utf-8"))["feeds"]

    def load_layers(self) -> list[dict]:
        return json.loads((ROOT / "config" / "layers.json").read_text(encoding="utf-8"))["layers"]


@lru_cache
def get_settings() -> Settings:
    return Settings()