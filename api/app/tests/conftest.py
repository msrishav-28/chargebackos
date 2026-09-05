from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models as m
from app.core.security import hash_password, hash_token
from app.db import Base, get_db
from app.domain.generate import generate_world
from app.domain.pipeline import score_raw
from app.main import app, settings
from app.services.seed import persist_scored, seed_profiles


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kwargs):
    # Test-only storage adapter. PostgreSQL remains the sole product database;
    # these tests verify behavior, not PostgreSQL locking or JSONB operators.
    return "JSON"


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        seed_profiles(session)
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def staff(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "test-only-secret-" + uuid4().hex)
    users = {}
    for role in ("viewer", "analyst", "reviewer", "admin"):
        user = m.OperatorUser(email=f"{role}@example.test", role=role, display_name=role,
                              password_hash=hash_password("test-password-only"), active=True)
        db.add(user)
        db.flush()
        token = uuid4().hex
        db.add(m.OperatorSession(user_id=user.id, token_hash=hash_token(token),
                                 expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        users[role] = (user, {"Authorization": f"Bearer {token}"})
    db.commit()
    return users


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def demo_cases(db, monkeypatch):
    def prediction(_bundle, raw):
        return {
            "modelVersion": "test-model", "featureVersion": "features-v1",
            "predictedCategory": "friendly_fraud_likely", "categoryConfidence": 0.95,
            "classScores": {"friendly_fraud_likely": 0.95, "merchant_service_issue": 0.02,
                            "true_fraud_likely": 0.02, "technical_or_insufficient_information": 0.01},
            "fightWorthinessProbability": 0.9, "expectedRecoveredValue": 2000,
            "shap": [], "calibrated": True,
        }

    monkeypatch.setattr("app.domain.pipeline.predict_case", prediction)
    raw = generate_world(42, 5)["cases"]
    scored = [score_raw({}, case) for case in raw]
    persist_scored(db, scored)
    db.commit()
    return {case["id"]: db.get(m.DisputeCase, case["id"]) for case in scored}
