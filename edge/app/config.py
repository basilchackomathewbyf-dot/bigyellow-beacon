from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BEACON_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vessel_id: str = "VSL-DEMO01"
    vessel_name: str = "MV Demo Star"
    edge_public_url: str = "http://192.168.1.10:8080"
    database_url: str = "postgresql+asyncpg://beacon:beacon@localhost:5433/beacon"
    model_url: str = "http://model:8081"
    edge_secret: str = "change-me"
    master_username: str = "master"
    master_pin: str = "1234"
    so_username: str = "safety"
    so_pin: str = "5678"
    shore_url: str = ""
    shore_vessel_key: str = ""
    sync_interval_s: int = 60
    link_mode: str = "auto"  # auto | forced_down
    asr_mode: str = "auto"  # gemma | whisper | auto
    k_anon: int = 5
    # Defaults suit no-Docker local dev; compose overrides to /data, /app/...
    data_dir: Path = Path("./data")
    ship_web_dist: Path = Path("../dashboards/ship-web/dist")
    contracts_dir: Path = Path("../contracts")


@lru_cache
def get_settings() -> Settings:
    return Settings()
