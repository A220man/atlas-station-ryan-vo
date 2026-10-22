import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "atlas-station"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./data/atlas.db"

    # Storage
    upload_dir: str = "./data/uploads"
    output_dir: str = "./data/outputs"
    max_upload_size_mb: int = 2048

    # Auth (Keycloak OIDC)
    oidc_enabled: bool = True
    oidc_issuer_url: str = "http://localhost:8080/realms/atlas"
    oidc_client_id: str = "atlas-frontend"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:3000/callback"
    oidc_scopes: str = "openid profile email roles"

    # LLM (optional)
    llm_api_key: str = ""
    llm_provider: str = "openai-compatible"
    llm_model: str = ""
    llm_base_url: str = ""

    # Processing
    worker_concurrency: int = 1
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_path(self) -> Path:
        p = Path(self.output_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()