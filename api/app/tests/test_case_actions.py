from app import models as m


def test_viewer_cannot_act(client, staff, demo_cases):
    response = client.post("/api/v1/disputes/CB-DEMO-01/prepare-draft", headers=staff["viewer"][1])
    assert response.status_code == 403
    detail = client.get("/api/v1/disputes/CB-DEMO-01", headers=staff["viewer"][1])
    assert detail.status_code == 200
    assert detail.json()["allowedActions"] == []


def test_analyst_cannot_approve_human_review(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    case.state = "human_review"
    db.commit()
    response = client.post(f"/api/v1/disputes/{case.id}/prepare-draft", headers=staff["analyst"][1])
    assert response.status_code == 403
    assert db.get(m.DisputeCase, case.id).state == "human_review"


def test_reviewer_approval_creates_completed_grounded_draft(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    case.state = "human_review"
    policy = db.query(m.PolicyDecision).filter_by(dispute_case_id=case.id).one()
    policy.allowed = False
    db.commit()
    response = client.post(f"/api/v1/disputes/{case.id}/prepare-draft", headers=staff["reviewer"][1])
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "draft_ready"
    assert result["draft"]["status"] == "completed"
    assert result["draft"]["citations"]
    assert "INR 4899.00" in result["draft"]["text"]
    assert db.query(m.PolicyDecision).filter_by(dispute_case_id=case.id).count() == 2
    assert db.query(m.CaseAction).filter_by(dispute_case_id=case.id).count() == 1


def test_review_cannot_bypass_missing_evidence(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-03"]
    case.state = "human_review"
    db.commit()
    for _ in range(2):
        response = client.post(f"/api/v1/disputes/{case.id}/prepare-draft", headers=staff["reviewer"][1])
        assert response.status_code == 409
    assert db.get(m.DisputeCase, case.id).state == "human_review"
    assert db.query(m.CaseAction).filter_by(dispute_case_id=case.id).count() == 0
    assert db.query(m.AuditEvent).filter_by(dispute_case_id=case.id, actor_type="human", event_type="action.blocked").count() == 2


def test_retry_completed_draft_does_not_duplicate_action(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    case.state = "policy_review"
    db.commit()
    for _ in range(2):
        response = client.post(f"/api/v1/disputes/{case.id}/prepare-draft", headers=staff["analyst"][1])
        assert response.status_code == 200
    assert db.query(m.CaseAction).filter_by(dispute_case_id=case.id).count() == 1


def test_invalid_transition_is_audited_and_does_not_write_case(client, db, staff, demo_cases):
    case = demo_cases["CB-DEMO-01"]
    case.state = "received"
    db.commit()
    response = client.post(f"/api/v1/disputes/{case.id}/prepare-draft", headers=staff["reviewer"][1])
    assert response.status_code == 409
    assert db.get(m.DisputeCase, case.id).state == "received"
    assert db.query(m.CaseAction).filter_by(dispute_case_id=case.id).count() == 0


def test_unknown_action_is_rejected(client, staff, demo_cases):
    response = client.post("/api/v1/disputes/CB-DEMO-01/action", headers=staff["analyst"][1], json={"action": "invented"})
    assert response.status_code == 422


def test_disabled_staff_cannot_sign_in(client, db, staff):
    staff["analyst"][0].active = False
    db.commit()
    response = client.post("/api/v1/auth/login", json={"email": "analyst@example.test", "password": "test-password-only"})
    assert response.status_code == 401
    assert client.get("/api/v1/auth/me", headers=staff["analyst"][1]).status_code == 401
