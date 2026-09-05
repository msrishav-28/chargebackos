import json
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import event

from app import models as m
from app.main import settings
from app.services.cases import serialize_cases


def test_queue_has_constant_query_count(db, demo_cases):
    statements = []
    def track(_connection, _cursor, statement, *_args):
        statements.append(statement)
    event.listen(db.bind, "before_cursor_execute", track)
    try:
        result = serialize_cases(db, list(demo_cases.values()))
    finally:
        event.remove(db.bind, "before_cursor_execute", track)
    assert len(result) == 5
    assert len(statements) == 4
    assert all(row["evidencePackage"]["items"] == [] for row in result)


def test_filters_use_latest_policy(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    old = db.query(m.PolicyDecision).filter_by(dispute_case_id=case.id).one()
    old.allowed = False
    db.add(m.PolicyDecision(
        dispute_case_id=case.id, policy_version=old.policy_version, profile=old.profile,
        allowed=True, recommended_action="prepare_representment_draft", fight_decision="contest_recommended",
        block_reasons_json=[], rules_evaluated_json=[], input_snapshot_hash=old.input_snapshot_hash,
        created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
    ))
    db.commit()
    result = client.get("/api/v1/disputes?blocked=true", headers=staff["viewer"][1])
    assert result.status_code == 200
    assert case.id not in [row["id"] for row in result.json()["items"]]


def test_queue_pages_are_disjoint(client, staff, demo_cases):
    ids = []
    for page in (1, 2, 3):
        result = client.get(f"/api/v1/disputes?limit=2&page={page}", headers=staff["viewer"][1])
        assert result.status_code == 200
        ids.extend(row["id"] for row in result.json()["items"])
    assert len(ids) == len(set(ids)) == 5


def test_rewrite_cannot_bypass_review(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    case.state = "human_review"
    db.commit()
    response = client.post(f"/api/v1/disputes/{case.id}/rewrite-draft", headers=staff["analyst"][1])
    assert response.status_code == 409
    assert db.query(m.AuditEvent).filter_by(dispute_case_id=case.id, event_type="action.blocked", actor_type="human").count() == 1


def test_rewrite_rejects_invented_facts_and_preserves_draft(client, db, staff, demo_cases, monkeypatch):
    monkeypatch.setattr(settings, "xai_api_key", "test-only-provider-key")
    monkeypatch.setattr("app.services.drafts.httpx.post", lambda *args, **kwargs: httpx.Response(
        200, request=httpx.Request("POST", "https://example.test"),
        json={"choices": [{"message": {"content": "Customer admitted fraud."}}]},
    ))
    before = db.query(m.RepresentmentDraft).filter_by(dispute_case_id="CB-DEMO-01").count()
    result = client.post("/api/v1/disputes/CB-DEMO-01/rewrite-draft", headers=staff["analyst"][1])
    assert result.status_code == 502
    assert db.query(m.RepresentmentDraft).filter_by(dispute_case_id="CB-DEMO-01").count() == before
    assert db.query(m.AuditEvent).filter_by(event_type="draft.failed").count() == 1


def test_rewrite_preserves_every_verified_paragraph(client, db, staff, demo_cases, monkeypatch):
    monkeypatch.setattr(settings, "xai_api_key", "test-only-provider-key")
    captured = []
    def provider(*args, **kwargs):
        paragraphs = json.loads(kwargs["json"]["messages"][1]["content"])["paragraphs"]
        captured.extend(paragraphs)
        return httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={
            "choices": [{"message": {"content": json.dumps({"order": list(range(len(paragraphs)))})}}],
        })
    monkeypatch.setattr("app.services.drafts.httpx.post", provider)
    result = client.post("/api/v1/disputes/CB-DEMO-01/rewrite-draft", headers=staff["analyst"][1])
    assert result.status_code == 200
    assert result.json()["draft"]["text"] == "\n\n".join(captured)
    assert result.json()["draft"]["citations"]
