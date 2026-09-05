"""Processing of stored synthetic records; simulation answers are never inputs."""
import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models as m
from app.domain.constants import EVIDENCE_LABELS, EVIDENCE_SCHEMAS, FEATURE_VERSION, POLICY_VERSION, REASON_CODES
from app.domain.generate import contest_cost, evidence_completeness
from app.domain.model import load_model, predict_case
from app.domain.policy import evaluate_policy
from app.services.cases import _latest, block_action, lock_case, record_event


class IngestBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    external_dispute_id: str = Field(min_length=1, max_length=64)
    merchant_id: str = Field(min_length=1, max_length=32)
    customer_id: str | None = Field(default=None, max_length=64)
    transaction_id: str = Field(min_length=1, max_length=64)
    reason_code: str = Field(min_length=1, max_length=32)
    disputed_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="INR", pattern="^INR$")
    received_at: AwareDatetime | None = None


def ingest_case(db: Session, body: IngestBody, actor: m.OperatorUser) -> m.DisputeCase:
    def existing():
        case = db.query(m.DisputeCase).filter_by(external_dispute_id=body.external_dispute_id).one_or_none()
        if case and (case.merchant_id != body.merchant_id or case.transaction_id != body.transaction_id
                     or case.reason_code != body.reason_code or case.disputed_amount != body.disputed_amount
                     or case.currency != body.currency or (body.customer_id and case.customer_id != body.customer_id)):
            block_action(db, case, actor, "This external dispute identifier already belongs to different records.")
        return case
    prior = existing()
    if prior:
        return prior
    txn = db.get(m.Transaction, body.transaction_id)
    if txn is None or txn.merchant_id != body.merchant_id or (body.customer_id and txn.customer_id != body.customer_id):
        raise HTTPException(status_code=422, detail="Transaction, merchant and customer must match stored synthetic records.")
    if body.disputed_amount > txn.amount or body.currency != txn.currency:
        raise HTTPException(status_code=422, detail="Disputed amount or currency does not match the stored transaction.")
    reason = next(((family, item["label"]) for family, items in REASON_CODES.items()
                   for item in items if item["code"] == body.reason_code), None)
    if reason is None:
        raise HTTPException(status_code=422, detail="Unsupported reason code.")
    opened = body.received_at or datetime.now(timezone.utc)
    paid = txn.transaction_at.replace(tzinfo=timezone.utc) if txn.transaction_at.tzinfo is None else txn.transaction_at
    if opened < paid or opened > datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Dispute time must be after payment and cannot be in the future.")
    source = (db.query(m.DisputeCase).filter_by(transaction_id=txn.id)
              .order_by(desc(m.DisputeCase.created_at), m.DisputeCase.id).first())
    order = db.query(m.Order).filter_by(transaction_id=txn.id).order_by(m.Order.id).first()
    case = m.DisputeCase(
        id="CB-" + uuid4().hex[:29], external_dispute_id=body.external_dispute_id,
        merchant_id=txn.merchant_id, customer_id=txn.customer_id, transaction_id=txn.id,
        order_id=order.id if order else None, reason_code=body.reason_code, reason_family=reason[0], reason_label=reason[1],
        disputed_amount=body.disputed_amount, currency=body.currency, state="received", split="operational",
        is_demo=False, customer_label="Synthetic customer", contest_cost=contest_cost(float(body.disputed_amount)), opened_at=opened,
    )
    try:
        db.add(case)
        db.flush()
    except IntegrityError:
        db.rollback()
        prior = existing()
        if prior:
            return prior
        raise
    record_event(db, case, "dispute.received", "Synthetic dispute received against verified stored transaction references.", actor)
    source_snapshot = _latest(db, m.FeatureSnapshot, source.id) if source else None
    if source_snapshot:
        snapshot = copy.deepcopy(source_snapshot.snapshot_json)
        features = copy.deepcopy(source_snapshot.features_json)
        hours = (opened - paid).total_seconds() / 3600
        snapshot["reasonContext"] = {"reasonCode": body.reason_code, "reasonFamily": reason[0], "hoursToDispute": hours}
        snapshot["evidenceSourceCaseId"] = source.id
        source_package = _latest(db, m.EvidencePackage, source.id)
        source_items = db.query(m.EvidenceItem).filter_by(package_id=source_package.id).all() if source_package else []
        available = {item.evidence_key for item in source_items
                     if item.present and item.source_reference and (item.value_json or {}).get("summary")}
        features.update(log_amount=math.log(max(1, float(body.disputed_amount))), hours_to_dispute=hours,
                        evidence_completeness=evidence_completeness(reason[0], available),
                        high_value_flag=float(body.disputed_amount >= 10000),
                        reason_unauthorized=float(reason[0] == "unauthorized"),
                        reason_not_received=float(reason[0] == "not_received"),
                        reason_service_issue=float(reason[0] == "service_issue"))
        db.add(m.FeatureSnapshot(dispute_case_id=case.id, feature_version=FEATURE_VERSION,
                                 features_json=features, snapshot_json=snapshot))
    case.state = "normalized"
    record_event(db, case, "case.normalized", "Reason code normalized; no transaction, evidence or outcome facts were invented.", actor, before="received")
    db.commit()
    return case


def triage_case(db: Session, case_id: str, actor: m.OperatorUser) -> m.DisputeCase:
    case = lock_case(db, case_id)
    if case.state not in {"normalized", "human_review"} or _latest(db, m.ModelPrediction, case.id):
        block_action(db, case, actor, "Triage requires a normalized case.", requested="triaged")
    bundle = load_model()
    snap = _latest(db, m.FeatureSnapshot, case.id)
    if bundle is None or snap is None:
        reason = "Model artifact unavailable." if bundle is None else "A complete frozen feature snapshot is unavailable."
        merchant = db.get(m.Merchant, case.merchant_id)
        db.add(m.PolicyDecision(
            dispute_case_id=case.id, policy_version=POLICY_VERSION, profile=merchant.policy_profile_id,
            allowed=False, recommended_action="request_human_review", fight_decision="human_review_required",
            block_reasons_json=["model_unavailable" if bundle is None else "snapshot_unavailable"],
            rules_evaluated_json=[{"rule": "model_and_snapshot_available", "passed": False, "detail": reason}],
            input_snapshot_hash=hashlib.sha256(f"{case.id}:{reason}".encode()).hexdigest(),
        ))
        case.state = "human_review"
        record_event(db, case, "case.routed_to_review", reason + " No score or draft was generated.", actor, before="normalized")
    else:
        pred = predict_case(bundle, {"features": snap.features_json, "disputedAmount": float(case.disputed_amount), "contestCost": float(case.contest_cost)})
        db.add(m.ModelPrediction(dispute_case_id=case.id, model_version=pred["modelVersion"], feature_version=pred["featureVersion"],
            predicted_category=pred["predictedCategory"], category_confidence=pred["categoryConfidence"],
            fight_worthiness_probability=pred["fightWorthinessProbability"], expected_recovered_value=pred["expectedRecoveredValue"],
            shap_summary_json=pred["shap"], raw_scores_json=pred["classScores"], calibrated=pred["calibrated"]))
        case.state = "triaged"
        record_event(db, case, "model.prediction_created", "Model scored the stored feature snapshot; simulation answers were excluded.", actor, before="normalized")
    db.commit()
    return case


def assemble_evidence(db: Session, case_id: str, actor: m.OperatorUser) -> m.DisputeCase:
    case = lock_case(db, case_id)
    if case.state not in {"triaged", "human_review"} or _latest(db, m.EvidencePackage, case.id):
        block_action(db, case, actor, "Evidence assembly requires a triaged or review case without a package.")
    snap = _latest(db, m.FeatureSnapshot, case.id)
    source_id = snap.snapshot_json.get("evidenceSourceCaseId") if snap else None
    source = db.get(m.DisputeCase, source_id) if source_id else None
    source_package = _latest(db, m.EvidencePackage, source.id) if source and source.transaction_id == case.transaction_id else None
    source_items = {i.evidence_key: i for i in db.query(m.EvidenceItem).filter_by(package_id=source_package.id).all()} if source_package else {}
    schema = next(s for s in EVIDENCE_SCHEMAS if s["reasonFamily"] == case.reason_family)
    items, missing = [], {"required": [], "preferred": []}
    for tier in ("required", "preferred", "optional"):
        for key in schema[tier]:
            src = source_items.get(key)
            present = bool(src and src.present and src.source_reference and (src.value_json or {}).get("summary"))
            if not present and tier in missing:
                missing[tier].append(key)
            items.append({"key": key, "tier": tier, "present": present, "source": src.source_reference if present else "",
                          "system": src.source_system if present else "stored_records", "type": src.evidence_type if src else "transaction",
                          "value": src.value_json if present else {"summary": "Not on file", "value": ""}})
    digest = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:16]
    package = m.EvidencePackage(dispute_case_id=case.id, reason_family=case.reason_family,
        completeness_score=evidence_completeness(case.reason_family, {i["key"] for i in items if i["present"]}),
        mandatory_complete=not missing["required"],
        missing_required_json=missing["required"], missing_preferred_json=missing["preferred"], package_hash=digest)
    db.add(package)
    db.flush()
    for item in items:
        db.add(m.EvidenceItem(id="ev-" + uuid4().hex, dispute_case_id=case.id, package_id=package.id,
            evidence_type=item["type"], evidence_key=item["key"], label=EVIDENCE_LABELS[item["key"]], tier=item["tier"],
            present=item["present"], is_required=item["tier"] == "required", source_system=item["system"],
            source_reference=item["source"], value_json=item["value"]))
    before = case.state
    if case.state == "triaged":
        case.state = "evidence_collecting"
    record_event(db, case, "evidence.package_completed", "Evidence assembled from stored source records; missing fields remain missing.", actor, before=before)
    db.commit()
    return case


def evaluate_case(db: Session, case_id: str, actor: m.OperatorUser) -> m.DisputeCase:
    case = lock_case(db, case_id)
    if case.state != "evidence_collecting":
        block_action(db, case, actor, "Policy evaluation requires completed evidence assembly.", requested="policy_review")
    pred, pkg, snap = (_latest(db, model, case.id) for model in (m.ModelPrediction, m.EvidencePackage, m.FeatureSnapshot))
    if pred is None or pkg is None or snap is None:
        block_action(db, case, actor, "A stored prediction, evidence package and snapshot are required.")
    merchant = db.get(m.Merchant, case.merchant_id)
    decision = evaluate_policy(profile_id=merchant.policy_profile_id, predicted_category=pred.predicted_category,
        category_confidence=float(pred.category_confidence), fight_worthiness=float(pred.fight_worthiness_probability),
        expected_recovered=float(pred.expected_recovered_value), mandatory_complete=pkg.mandatory_complete,
        missing_required=pkg.missing_required_json, package_hash=pkg.package_hash, refund_requested=snap.features_json["refund_requested"],
        delivery_confirmed=snap.features_json["delivery_confirmed"], reason_family=case.reason_family, case_state=case.state, calibrated=pred.calibrated,
        auto_prep_rate=(db.query(m.DisputeCase).filter_by(merchant_id=case.merchant_id, state="draft_ready").count() + 1)
        / max(1, db.query(m.DisputeCase).filter_by(merchant_id=case.merchant_id).count()))
    db.add(m.PolicyDecision(dispute_case_id=case.id, policy_version=decision["policyVersion"], profile=decision["profile"],
        allowed=decision["allowed"], recommended_action=decision["recommendedAction"], fight_decision=decision["fightDecision"],
        block_reasons_json=decision["blockReasons"], rules_evaluated_json=decision["rulesEvaluated"], input_snapshot_hash=decision["inputSnapshotHash"]))
    case.state = "policy_review" if pkg.mandatory_complete else "evidence_incomplete"
    record_event(db, case, "policy.evaluated", "Policy decision stored. Draft preparation remains a separate controlled action.", actor, before="evidence_collecting")
    db.commit()
    return case
