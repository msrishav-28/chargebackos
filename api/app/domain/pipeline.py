from datetime import datetime, timedelta

from app.domain.draft import build_grounded_draft
from app.domain.lifecycle import make_audit, state_from_policy
from app.domain.model import predict_case
from app.domain.policy import evaluate_policy


def score_raw(bundle: dict, raw: dict, auto_prep_rate: float | None = None) -> dict:
    prediction = predict_case(bundle, raw)
    policy = evaluate_policy(
        profile_id=raw["merchant"]["policyProfile"],
        predicted_category=prediction["predictedCategory"],
        category_confidence=prediction["categoryConfidence"],
        fight_worthiness=prediction["fightWorthinessProbability"],
        expected_recovered=prediction["expectedRecoveredValue"],
        mandatory_complete=raw["evidencePackage"]["mandatoryComplete"],
        missing_required=raw["evidencePackage"]["missingRequired"],
        package_hash=raw["evidencePackage"]["packageHash"],
        refund_requested=raw["features"]["refund_requested"],
        delivery_confirmed=raw["features"]["delivery_confirmed"],
        reason_family=raw["reasonFamily"],
        auto_prep_rate=auto_prep_rate,
        case_state="evidence_collecting",
        calibrated=prediction["calibrated"],
    )
    state = state_from_policy(policy["recommendedAction"], raw["evidencePackage"]["mandatoryComplete"])
    draft = build_grounded_draft(raw=raw, evidence=raw["evidencePackage"], policy=policy)
    if not policy["allowed"]:
        draft = {**draft, "status": "blocked"}
    timeline = [
        make_audit(raw["id"], "dispute.received", "Dispute event ingested from synthetic issuer feed.", after="received", actor="simulation", at=raw["openedAt"]),
        make_audit(raw["id"], "case.normalized", "Reason code mapped to internal family taxonomy.", before="received", after="normalized"),
        make_audit(raw["id"], "model.prediction_created", "Calibrated category and fight-worthiness scored on frozen feature snapshot.", before="normalized", after="triaged", actor="model"),
        make_audit(raw["id"], "evidence.package_completed", "Reason-family evidence schema assembled. No fields invented.", before="triaged", after="evidence_collecting"),
        make_audit(raw["id"], "policy.evaluated", "Deterministic policy engine evaluated. Model output cannot execute an action.", before="evidence_collecting", after="evidence_incomplete" if state == "evidence_incomplete" else "policy_review", actor="policy"),
    ]
    if state == "evidence_incomplete":
        timeline.append(make_audit(raw["id"], "action.blocked", "Missing required evidence blocked automated representment.", before="evidence_incomplete", after="evidence_incomplete", actor="policy"))
    elif state == "human_review":
        timeline.append(make_audit(raw["id"], "case.routed_to_review", "Policy routed the case to a human reviewer.", before="policy_review", after="human_review", actor="policy"))
    elif state == "not_contested":
        timeline.append(make_audit(raw["id"], "case.closed", "Policy recommended not contesting (economics or win probability).", before="policy_review", after="not_contested", actor="policy"))
    else:
        timeline.append(make_audit(raw["id"], "draft.generated", "Evidence-grounded representment draft prepared. No live submission.", before="policy_review", after="draft_ready"))
    opened = datetime.fromisoformat(raw["openedAt"].replace("Z", "+00:00"))
    for index, event in enumerate(timeline):
        event["at"] = (opened + timedelta(milliseconds=index)).isoformat()
    return {**raw, "prediction": prediction, "policyDecision": policy, "state": state, "draft": draft, "timeline": timeline}
