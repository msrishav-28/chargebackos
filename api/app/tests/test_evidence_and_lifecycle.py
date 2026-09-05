from app.domain.constants import EVIDENCE_SCHEMAS, POLICY_PROFILES
from app.domain.lifecycle import can_transition, operator_actions, target_state


def test_evidence_yaml_has_four_families():
    families = {s["reasonFamily"] for s in EVIDENCE_SCHEMAS}
    assert families == {"unauthorized", "not_received", "service_issue", "other"}
    for schema in EVIDENCE_SCHEMAS:
        assert "transaction_record" in schema["required"]
        assert schema["preferred"]
        assert schema["optional"] or schema["reasonFamily"] == "other"


def test_policy_profiles_exist():
    assert set(POLICY_PROFILES) == {"conservative", "balanced", "aggressive"}
    assert POLICY_PROFILES["aggressive"]["minConfidence"] < POLICY_PROFILES["conservative"]["minConfidence"]


def test_target_state_mapping():
    assert target_state("prepare_representment_draft") == "draft_ready"
    assert target_state("request_human_review") == "human_review"
    assert target_state("recommend_do_not_contest") == "not_contested"
    assert target_state("close_case") == "closed"


def test_reviewer_can_approve_draft_from_human_review():
    assert can_transition("human_review", "draft_ready") is True
    assert can_transition("evidence_incomplete", "draft_ready") is False


def test_operator_actions_hide_moves_the_server_would_refuse():
    draft_ready = operator_actions("draft_ready", "analyst", policy_allowed=True, mandatory_complete=True)
    assert draft_ready == ["prepare_representment_draft"]
    assert "close_case" not in operator_actions("draft_ready", "admin", policy_allowed=True, mandatory_complete=True)
    assert operator_actions("evidence_incomplete", "analyst", policy_allowed=False, mandatory_complete=False) == ["request_human_review"]
    assert operator_actions("draft_ready", "viewer", policy_allowed=True, mandatory_complete=True) == []
    assert "prepare_representment_draft" not in operator_actions("human_review", "analyst", policy_allowed=False, mandatory_complete=True)
    assert "prepare_representment_draft" in operator_actions("human_review", "reviewer", policy_allowed=False, mandatory_complete=True)
