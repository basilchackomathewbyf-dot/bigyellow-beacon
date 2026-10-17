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

    vessel_id: str = "v-0007"
    vessel_code: str = "0007"
    vessel_name: str = "MV Demo Star"
    vessel_secret: str = "demo-vessel-secret-v-0007"
    edge_url: str = "https://beacon.ship.local:8443"
    edge_public_url: str | None = None
    database_url: str = "postgresql+asyncpg://beacon:beacon@localhost:5433/beacon"
    # Required at startup (≥ 32 chars). Empty default forces explicit env/test setup.
    jwt_secret: str = ""
    ai: str = "fake"  # fake | ollama
    ollama_url: str = "http://localhost:11434"
    shore_url: str = "http://127.0.0.1:9090"
    shore_api_key: str = ""
    link_override: str = "auto"  # auto | up | down
    k_anon: int = 5
    data_dir: Path = Path("./data")
    web_dist: Path = Path("../web/apps/crew/dist")
    ship_web_dist: Path | None = None
    roster_file: Path = Path("../seed/crew_v-0007.json")

    @property
    def public_edge_url(self) -> str:
        return self.edge_public_url or self.edge_url

    @property
    def crew_web_dist(self) -> Path:
        return self.ship_web_dist or self.web_dist


@lru_cache
def get_settings() -> Settings:
    return Settings()
