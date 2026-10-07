from functools import lru_cache
from typing import Literal
from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://chargebackos:chargebackos@127.0.0.1:5432/chargebackos"
    database_url_direct: str = ""
    auth_secret: str = "change-me-to-a-long-random-string"
    demo_password: str = "change-me-demo"
    api_cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    web_origin: str = ""
    xai_api_key: str = ""
    seed: Literal[42] = 42
    dispute_target: int = Field(default=1500, ge=500, le=5000)

    @staticmethod
    def as_sqlalchemy(url: str) -> str:
        u = url.strip()
        if not u:
            return u
        if u.startswith("postgres://"):
            u = "postgresql+psycopg://" + u[len("postgres://") :]
        elif u.startswith("postgresql://") and "+psycopg" not in u.split(":", 1)[0]:
            u = "postgresql+psycopg://" + u[len("postgresql://") :]
        host = (make_url(u).host or "").lower()
        hosted = any(host == domain or host.endswith("." + domain)
                     for domain in ("supabase.co", "supabase.com", "neon.tech"))
        if "sslmode=" not in u and hosted:
            u += ("&" if "?" in u else "?") + "sslmode=require"
        return u

    @property
    def database_connect_args(self) -> dict:
        url = make_url(self.runtime_database_url)
        if url.drivername != "postgresql+psycopg":
            return {}
        # Bound outages and support Supavisor transaction pooling if selected.
        # Session pooling (5432) remains the default for this persistent API.
        return {"connect_timeout": 10, "prepare_threshold": None}

    @property
    def runtime_database_url(self) -> str:
        return self.as_sqlalchemy(self.database_url)

    @property
    def migration_database_url(self) -> str:
        direct = self.database_url_direct.strip() or self.database_url
        result = self.as_sqlalchemy(direct)
        url = make_url(result)
        host = (url.host or "").lower()
        if url.port == 6543 and any(host.endswith("." + domain) for domain in ("supabase.co", "supabase.com")):
            raise ValueError("Use a Supabase direct or session-pooler connection on port 5432 for DATABASE_URL_DIRECT.")
        return result

    @property
    def cors_origin_list(self) -> list[str]:
        extra = [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]
        if self.web_origin.strip():
            extra.append(self.web_origin.strip())
        return list(dict.fromkeys(extra))


@lru_cache
def get_settings() -> Settings:
    return Settings()
