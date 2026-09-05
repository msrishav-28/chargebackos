import pytest

from app import models as m


def body(case, **overrides):
    return {"external_dispute_id": "external-new-test", "merchant_id": case.merchant_id,
            "transaction_id": case.transaction_id, "customer_id": case.customer_id,
            "reason_code": case.reason_code, "disputed_amount": str(case.disputed_amount), **overrides}


def test_ingest_uses_referenced_records_and_is_idempotent(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    payload = body(case)
    first = client.post("/api/v1/disputes/ingest", headers=staff["analyst"][1], json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/disputes/ingest", headers=staff["analyst"][1], json=payload)
    assert second.json()["id"] == first.json()["id"]
    assert first.json()["transactionId"] == case.transaction_id
    assert first.json()["trueCategory"] is None
    assert first.json()["simulatedOutcome"] is None
    assert db.query(m.Transaction).count() == 5
    assert db.query(m.DisputeCase).count() == 6
    conflict = client.post("/api/v1/disputes/ingest", headers=staff["analyst"][1], json=body(case, disputed_amount="1.00"))
    assert conflict.status_code == 409


def test_ingest_rejects_mismatched_references_and_invalid_money(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    for changes in ({"merchant_id": "other"}, {"customer_id": "other"}, {"disputed_amount": "NaN"},
                    {"disputed_amount": "1.001"}, {"reason_code": "invented"}, {"currency": "USD"}):
        result = client.post("/api/v1/disputes/ingest", headers=staff["analyst"][1], json=body(case, **changes))
        assert result.status_code == 422
    assert db.query(m.DisputeCase).count() == 5


def test_missing_model_creates_review_decision_without_score(client, db, staff, demo_cases, monkeypatch):
    monkeypatch.setattr("app.services.processing.load_model", lambda: None)
    created = client.post("/api/v1/disputes/ingest", headers=staff["analyst"][1], json=body(demo_cases["CB-DEMO-01"])).json()
    result = client.post(f"/api/v1/disputes/{created['id']}/triage", headers=staff["analyst"][1])
    assert result.status_code == 200
    assert result.json()["state"] == "human_review"
    assert result.json()["prediction"] is None
    assert result.json()["policyDecision"]["allowed"] is False


def test_complete_processing_requires_all_stages(client, db, staff, demo_cases, monkeypatch):
    import app.domain.pipeline as pipeline
    monkeypatch.setattr("app.services.processing.load_model", lambda: {})
    monkeypatch.setattr("app.services.processing.predict_case", pipeline.predict_case)
    created = client.post("/api/v1/disputes/ingest", headers=staff["analyst"][1], json=body(demo_cases["CB-DEMO-01"])).json()
    path = f"/api/v1/disputes/{created['id']}"
    assert client.post(path + "/evaluate-policy", headers=staff["analyst"][1]).status_code == 409
    for step, state in (("triage", "triaged"), ("assemble-evidence", "evidence_collecting"), ("evaluate-policy", "policy_review")):
        result = client.post(path + "/" + step, headers=staff["analyst"][1])
        assert result.status_code == 200, result.text
        assert result.json()["state"] == state
    assert result.json()["evidencePackage"]["mandatoryComplete"] is True
    from app.services.cases import _latest
    snapshot = _latest(db, m.FeatureSnapshot, created["id"])
    assert snapshot.features_json["evidence_completeness"] == pytest.approx(result.json()["evidencePackage"]["completenessScore"])
    import math
    assert snapshot.features_json["log_amount"] == math.log(float(demo_cases["CB-DEMO-01"].disputed_amount))
    assert client.post(path + "/triage", headers=staff["analyst"][1]).status_code == 409


def test_seeded_timeline_is_chronological(db, demo_cases):
    events = db.query(m.AuditEvent).filter_by(dispute_case_id="CB-DEMO-03").order_by(m.AuditEvent.created_at).all()
    assert [event.event_type for event in events] == ["dispute.received", "case.normalized", "model.prediction_created",
        "evidence.package_completed", "policy.evaluated", "action.blocked"]
    assert len({event.created_at for event in events}) == len(events)
