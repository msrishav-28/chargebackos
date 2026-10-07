"""Run only against the explicitly configured disposable CI database."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.core.config import Settings


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="Requires disposable PostgreSQL")
def test_migrations_deny_browser_roles_and_allow_backend():
    url = Settings.as_sqlalchemy(os.environ["TEST_POSTGRES_URL"])
    engine = create_engine(url)
    with engine.begin() as connection:
        # These roles emulate Supabase defaults on an empty CI database.
        connection.execute(text("CREATE ROLE anon NOLOGIN"))
        connection.execute(text("CREATE ROLE authenticated NOLOGIN"))
        connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated"))
    env = {**os.environ, "DATABASE_URL": url, "DATABASE_URL_DIRECT": url}
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    with engine.begin() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_backend_only_access"
        assert connection.execute(text("SELECT count(*) FROM operator_users")).scalar_one() == 0
        tables = connection.execute(text("SELECT relname, relrowsecurity FROM pg_class JOIN pg_namespace n ON n.oid = relnamespace WHERE n.nspname = 'public' AND relkind = 'r'")).all()
        assert len(tables) == 21
        for name, rls in tables:
            assert rls, name
            for role in ("anon", "authenticated"):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    assert not connection.execute(text("SELECT has_table_privilege(:role, :table, :privilege)"),
                        {"role": role, "table": f"public.{name}", "privilege": privilege}).scalar_one()
    engine.dispose()
