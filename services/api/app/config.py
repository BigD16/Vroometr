from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# services/api/app/config.py → repo root
REPO_ROOT = Path(__file__).resolve().parents[3]


def _env_files() -> tuple[Path, ...]:
    """`.env.example` holds documented defaults; `.env` overrides them."""
    files = [REPO_ROOT / ".env.example"]
    local = REPO_ROOT / ".env"
    if local.exists():
        files.append(local)
    return tuple(files)


class Settings(BaseSettings):
    """Runtime config. Values come from `.env` / `.env.example`, not from this file."""

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    redis_url: str

    aws_endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_default_region: str
    s3_bucket: str

    api_host: str
    api_port: int

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
