import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings


@pytest.mark.parametrize("host", ["db.example.supabase.co", "aws-0-region.pooler.supabase.com", "ep-example.neon.tech"])
def test_hosted_connections_add_tls_and_preserve_encoded_password(host):
    result = Settings.as_sqlalchemy(f"postgres://postgres:p%40ss%25word@{host}:5432/postgres")
    parsed = make_url(result)
    assert parsed.password == "p@ss%word"
    assert parsed.query["sslmode"] == "require"
    assert parsed.drivername == "postgresql+psycopg"


def test_explicit_tls_and_local_connections_are_preserved():
    url = "postgresql://user:pass@db.example.supabase.co:5432/postgres?sslmode=verify-full"
    assert make_url(Settings.as_sqlalchemy(url)).query["sslmode"] == "verify-full"
    assert "sslmode" not in Settings.as_sqlalchemy("postgresql://u:p@localhost/db")
    assert "sslmode" not in Settings.as_sqlalchemy("postgresql://u:p@supabase.co.example.org/db")


def test_pooler_runtime_and_migration_connections():
    settings = Settings(_env_file=None,
        database_url="postgresql://postgres.ref:pw@aws-0-region.pooler.supabase.com:6543/postgres",
        database_url_direct="postgresql://postgres.ref:pw@aws-0-region.pooler.supabase.com:5432/postgres")
    assert settings.database_connect_args == {"connect_timeout": 10, "prepare_threshold": None}
    assert make_url(settings.migration_database_url).port == 5432
    settings.database_url_direct = ""
    with pytest.raises(ValueError, match="session-pooler"):
        _ = settings.migration_database_url


def test_alembic_accepts_percent_encoded_password_without_connecting(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://postgres:p%40ss%25word@localhost:5432/postgres")
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "ENABLE ROW LEVEL SECURITY" in result.stdout
