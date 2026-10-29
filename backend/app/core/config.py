"""Application configuration — loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_PROJECT_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Exasol ────────────────────────────────────────────────────────────
    exasol_host: str = "localhost"
    exasol_port: int = 8563
    exasol_user: str = "sys"
    exasol_password: str = "exasol"
    exasol_schema: str = "SUPPLYLENS"

    # ── Backend ───────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    secret_key: str = "dev-secret-key"
    environment: str = "development"

    # ── Optional LLM ──────────────────────────────────────────────────────
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""

    # ── Data ──────────────────────────────────────────────────────────────
    data_dir: Path = _PROJECT_ROOT / "data"
    upload_dir: Path = _PROJECT_ROOT / "data" / "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @property
    def exasol_dsn(self) -> str:
        return f"{self.exasol_host}:{self.exasol_port}"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()
