from app.domain.constants import COST_ASSUMPTIONS, NOW_ISO, POLICY_PROFILES, POLICY_VERSION
import hashlib
import json
import math


def expected_value(
    p_win: float,
    amount: float,
    contest_cost: float,
    fp_fixed: float | None = None,
    fp_var: float | None = None,
) -> float:
    fp_fixed = COST_ASSUMPTIONS["fpPenaltyFixed"] if fp_fixed is None else fp_fixed
    fp_var = COST_ASSUMPTIONS["fpPenaltyVariable"] if fp_var is None else fp_var
    fp_penalty = fp_fixed + fp_var * amount
    return p_win * amount - contest_cost - (1 - p_win) * fp_penalty


def evaluate_policy(
    *,
    profile_id: str,
    predicted_category: str,
    category_confidence: float,
    fight_worthiness: float,
    expected_recovered: float,
    mandatory_complete: bool,
    missing_required: list[str],
    package_hash: str,
    refund_requested: float,
    delivery_confirmed: float,
    reason_family: str,
    auto_prep_rate: float | None = None,
    case_state: str = "policy_review",
    calibrated: bool = True,
) -> dict:
    if not all(math.isfinite(v) for v in (category_confidence, fight_worthiness, expected_recovered)):
        raise ValueError("Policy inputs must be finite.")
    if not 0 <= category_confidence <= 1 or not 0 <= fight_worthiness <= 1:
        raise ValueError("Policy probabilities must be between zero and one.")
    policy = POLICY_PROFILES[profile_id]
    block_reasons: list[str] = []
    rules: list[dict] = []

    def rule(name: str, passed: bool, detail: str, block: str | None = None) -> None:
        rules.append({"rule": name, "passed": passed, "detail": detail})
        if not passed and block:
            block_reasons.append(block)

    state_ok = case_state in {"policy_review", "evidence_collecting"}
    rule("case_state_evaluable", state_ok, f"Current case state: {case_state}.", "case_state_not_evaluable")
    rule("calibrated_model", calibrated, "A calibrated model is required for automated preparation.", "model_not_calibrated")
    ev_ok = mandatory_complete and not missing_required
    rule(
        "mandatory_evidence_complete",
        ev_ok,
        "All required evidence fields are present." if ev_ok else f"Missing required: {', '.join(missing_required)}",
        "missing_required_evidence",
    )
    conf_ok = category_confidence >= policy["minConfidence"]
    rule(
        "classification_confidence",
        conf_ok,
        f"Calibrated confidence {category_confidence:.2f} vs min {policy['minConfidence']:.2f}.",
        "low_model_confidence",
    )
    win_ok = fight_worthiness >= policy["minWinProbability"]
    rule(
        "win_probability",
        win_ok,
        f"Calibrated p(win) {fight_worthiness:.2f} vs min {policy['minWinProbability']:.2f}.",
        "low_expected_win_probability",
    )
    ev_value_ok = expected_recovered >= policy["minExpectedValue"]
    rule(
        "expected_value",
        ev_value_ok,
        f"Expected recovered value {expected_recovered:.0f} vs min {policy['minExpectedValue']}.",
        "negative_expected_value",
    )
    sensitive = predicted_category == "true_fraud_likely"
    rule(
        "sensitive_category_gate",
        not sensitive,
        "Category is not in the sensitive set." if not sensitive else "True-fraud-likely routes to human review.",
        "sensitive_risk_category",
    )
    conflicting = refund_requested == 1 and delivery_confirmed == 1 and reason_family == "not_received"
    rule(
        "conflicting_support_evidence",
        not conflicting,
        "No conflicting support/fulfillment evidence." if not conflicting else "Delivery conflicts with not-received + refund.",
        "conflicting_evidence",
    )
    tech = predicted_category == "technical_or_insufficient_information"
    rule(
        "insufficient_information",
        not tech,
        "Category is information-complete enough to consider automation." if not tech else "Insufficient-information cannot auto-prepare.",
        "insufficient_information",
    )
    rate_ok = True
    if auto_prep_rate is not None:
        rate_ok = auto_prep_rate <= policy["maxAutoPrepRate"]
        rule(
            "max_auto_prep_rate",
            rate_ok,
            f"Book auto-prep rate {auto_prep_rate:.2f} vs max {policy['maxAutoPrepRate']:.2f}.",
            "auto_prep_rate_exceeded",
        )

    allowed = True
    recommended = "prepare_representment_draft"
    fight = "contest_recommended"
    if not state_ok or not calibrated:
        recommended, fight, allowed = "request_human_review", "human_review_required", False
    elif not ev_ok:
        recommended, fight, allowed = "mark_evidence_incomplete", "human_review_required", False
    elif sensitive:
        recommended, fight, allowed = "request_human_review", "human_review_required", False
    elif tech or conflicting or not conf_ok:
        recommended, fight, allowed = "request_human_review", "human_review_required", False
    elif not win_ok or not ev_value_ok or not rate_ok:
        recommended, fight, allowed = "recommend_do_not_contest", "do_not_contest", False

    return {
        "policyVersion": POLICY_VERSION,
        "profile": profile_id,
        "allowed": allowed,
        "recommendedAction": recommended,
        "fightDecision": fight,
        "blockReasons": block_reasons,
        "rulesEvaluated": rules,
        "inputSnapshotHash": hashlib.sha256(json.dumps({
            "version": POLICY_VERSION, "profile": profile_id, "category": predicted_category,
            "confidence": category_confidence, "winProbability": fight_worthiness,
            "expectedValue": expected_recovered, "packageHash": package_hash,
            "mandatoryComplete": mandatory_complete, "missingRequired": missing_required,
            "refundRequested": refund_requested, "deliveryConfirmed": delivery_confirmed,
            "reasonFamily": reason_family, "autoPrepRate": auto_prep_rate,
            "state": case_state, "calibrated": calibrated,
        }, sort_keys=True, allow_nan=False).encode()).hexdigest(),
        "evaluatedAt": NOW_ISO,
    }
