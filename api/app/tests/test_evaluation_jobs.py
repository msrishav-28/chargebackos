from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app import models as m
from app.domain.constants import DATASET_VERSION, MODEL_VERSION, POLICY_VERSION


@pytest.fixture
def seeded_run(db):
    run = m.BatchRun(id=uuid4(), scenario_name="test", strategy="ml_policy", random_seed=42,
        dataset_version=DATASET_VERSION, model_version=MODEL_VERSION, policy_version=POLICY_VERSION,
        state="completed", config_json={"n": 1500}, summary_json={}, completed_at=datetime.now(timezone.utc))
    db.add(run)
    db.commit()
    return run


def test_evaluation_creates_real_job_and_retry_reuses_it(client, db, staff, seeded_run, monkeypatch):
    monkeypatch.setattr("app.services.evaluations.load_model", lambda: {"modelVersion": MODEL_VERSION, "nCases": 1500})
    dispatched = []
    monkeypatch.setattr("app.main.execute_evaluation", dispatched.append)
    headers = {**staff["admin"][1], "Idempotency-Key": "test-run"}
    first = client.post("/api/v1/evaluations/run", headers=headers)
    second = client.post("/api/v1/evaluations/run", headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json()["batchRunId"] != str(seeded_run.id)
    assert first.json() == second.json()
    assert len(dispatched) == 1
    assert db.query(m.BatchRun).count() == 2


def test_evaluation_rejects_non_admin_and_missing_model(client, staff, seeded_run, monkeypatch):
    assert client.post("/api/v1/evaluations/run", headers=staff["analyst"][1]).status_code == 403
    monkeypatch.setattr("app.services.evaluations.load_model", lambda: None)
    assert client.post("/api/v1/evaluations/run", headers=staff["admin"][1]).status_code == 503
    assert client.get("/api/v1/evaluations/not-a-uuid", headers=staff["viewer"][1]).status_code == 422


def test_reset_requires_explicit_confirmation(client, staff):
    assert client.post("/api/v1/demo/reset", headers=staff["admin"][1]).status_code == 422
