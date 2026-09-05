from app.domain.lifecycle import can_transition
from app.domain.policy import evaluate_policy, expected_value


def _base(**kwargs):
    payload = dict(
        profile_id="balanced",
        predicted_category="friendly_fraud_likely",
        category_confidence=0.9,
        fight_worthiness=0.8,
        expected_recovered=2000,
        mandatory_complete=True,
        missing_required=[],
        package_hash="abcd",
        refund_requested=0,
        delivery_confirmed=1,
        reason_family="not_received",
    )
    payload.update(kwargs)
    return evaluate_policy(**payload)


def test_missing_evidence_blocks_draft():
    d = _base(mandatory_complete=False, missing_required=["Order confirmation"])
    assert d["allowed"] is False
    assert d["recommendedAction"] == "mark_evidence_incomplete"
    assert "missing_required_evidence" in d["blockReasons"]


def test_true_fraud_routes_to_review():
    d = _base(predicted_category="true_fraud_likely")
    assert d["allowed"] is False
    assert d["recommendedAction"] == "request_human_review"


def test_passing_policy_allows_draft():
    d = _base()
    assert d["allowed"] is True
    assert d["recommendedAction"] == "prepare_representment_draft"


def test_expected_value_penalizes_false_positives():
    low = expected_value(0.05, 10000, 400)
    high = expected_value(0.9, 10000, 400)
    assert low < high
    assert low < 0


def test_illegal_transition_blocked():
    assert can_transition("received", "draft_ready") is False
    assert can_transition("human_review", "draft_ready") is True
