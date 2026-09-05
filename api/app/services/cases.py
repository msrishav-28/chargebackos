from __future__ import annotations

from datetime import datetime, timezone
from typing import NoReturn

from fastapi import HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, aliased

from app import models as m
from app.domain.draft import build_grounded_draft, validate_draft_evidence
from app.domain.evaluation import settle
from app.domain.lifecycle import can_transition, make_audit, operator_actions, target_state


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).isoformat()


def _f(v):
    return float(v) if v is not None else None


def _latest(db: Session, model, case_id: str, loaded: dict | None = None):
    if loaded is not None:
        return loaded[model].get(case_id)
    return (db.query(model).filter(model.dispute_case_id == case_id)
            .order_by(desc(model.created_at), desc(model.id)).first())


def serialize_cases(db: Session, cases: list[m.DisputeCase]) -> list[dict]:
    if not cases:
        return []
    ids = [case.id for case in cases]
    loaded = {m.Merchant: {row.id: row for row in db.query(m.Merchant)
                          .filter(m.Merchant.id.in_({case.merchant_id for case in cases})).all()}}
    for model in (m.ModelPrediction, m.EvidencePackage, m.PolicyDecision):
        ranked = (db.query(model, func.row_number().over(
            partition_by=model.dispute_case_id, order_by=(model.created_at.desc(), model.id.desc())
        ).label("position")).filter(model.dispute_case_id.in_(ids)).subquery())
        rows = db.query(aliased(model, ranked)).filter(ranked.c.position == 1).all()
        loaded[model] = {row.dispute_case_id: row for row in rows}
    return [serialize_case(db, case, loaded=loaded) for case in cases]


def serialize_case(db: Session, case: m.DisputeCase, *, full: bool = False, loaded: dict | None = None, actor: m.OperatorUser | None = None) -> dict:
    mer = loaded[m.Merchant].get(case.merchant_id) if loaded is not None else db.get(m.Merchant, case.merchant_id)
    pred = _latest(db, m.ModelPrediction, case.id, loaded)
    pkg = _latest(db, m.EvidencePackage, case.id, loaded)
    pol = _latest(db, m.PolicyDecision, case.id, loaded)
    base = {
        "id": case.id,
        "externalDisputeId": case.external_dispute_id,
        "merchantId": case.merchant_id,
        "merchantName": mer.name if mer else case.merchant_id,
        "merchantSegment": mer.segment if mer else None,
        "policyProfile": mer.policy_profile_id if mer else None,
        "customerId": case.customer_id,
        "customerLabel": case.customer_label,
        "transactionId": case.transaction_id,
        "orderId": case.order_id,
        "reasonCode": case.reason_code,
        "reasonFamily": case.reason_family,
        "reasonLabel": case.reason_label,
        "disputedAmount": _f(case.disputed_amount),
        "currency": case.currency,
        "state": case.state,
        "split": case.split,
        "isDemo": case.is_demo,
        "demoRole": case.demo_role,
        "openedAt": _iso(case.opened_at),
        "contestCost": _f(case.contest_cost),
        "status": case.state,
        "caseStage": case.state,
        "prediction": None,
        "policyDecision": None,
        "evidencePackage": None,
    }
    if pred:
        base["prediction"] = {
            "modelVersion": pred.model_version,
            "featureVersion": pred.feature_version,
            "predictedCategory": pred.predicted_category,
            "categoryConfidence": _f(pred.category_confidence),
            "classScores": pred.raw_scores_json,
            "fightWorthinessProbability": _f(pred.fight_worthiness_probability),
            "expectedRecoveredValue": _f(pred.expected_recovered_value),
            "shap": pred.shap_summary_json,
            "calibrated": pred.calibrated,
        }
        base["modelSummary"] = {
            "category": pred.predicted_category,
            "confidence": _f(pred.category_confidence),
            "pWin": _f(pred.fight_worthiness_probability),
        }
    if pol:
        base["policyDecision"] = {
            "policyVersion": pol.policy_version,
            "profile": pol.profile,
            "allowed": pol.allowed,
            "recommendedAction": pol.recommended_action,
            "fightDecision": pol.fight_decision,
            "blockReasons": pol.block_reasons_json,
            "rulesEvaluated": pol.rules_evaluated_json,
            "inputSnapshotHash": pol.input_snapshot_hash,
            "evaluatedAt": _iso(pol.created_at),
        }
        base["policySummary"] = {
            "allowed": pol.allowed,
            "action": pol.recommended_action,
            "reasons": pol.block_reasons_json,
        }
        base["currentAction"] = pol.recommended_action
    if pkg:
        items = db.query(m.EvidenceItem).filter(m.EvidenceItem.package_id == pkg.id).order_by(m.EvidenceItem.id).all() if full else []
        base["evidencePackage"] = {
            "reasonFamily": pkg.reason_family,
            "completenessScore": _f(pkg.completeness_score),
            "mandatoryComplete": pkg.mandatory_complete,
            "missingRequired": pkg.missing_required_json,
            "missingPreferred": pkg.missing_preferred_json,
            "packageHash": pkg.package_hash,
            "items": [
                {
                    "id": it.id,
                    "type": it.evidence_type,
                    "key": it.evidence_key,
                    "label": it.label,
                    "tier": it.tier,
                    "present": it.present,
                    "sourceSystem": it.source_system,
                    "sourceReference": it.source_reference,
                    "summary": (it.value_json or {}).get("summary", ""),
                    "value": (it.value_json or {}).get("value", ""),
                }
                for it in items
            ],
        }
        base["evidenceSummary"] = {
            "completeness": _f(pkg.completeness_score),
            "mandatoryComplete": pkg.mandatory_complete,
        }
    if not full:
        return base
    base["allowedActions"] = operator_actions(
        case.state,
        actor.role if actor else "viewer",
        policy_allowed=bool(pol and pol.allowed),
        mandatory_complete=bool(pkg and pkg.mandatory_complete),
    )
    label = db.get(m.SimulationLabel, case.id)
    snap = (
        db.query(m.FeatureSnapshot)
        .filter(m.FeatureSnapshot.dispute_case_id == case.id)
        .order_by(desc(m.FeatureSnapshot.created_at))
        .first()
    )
    draft = (
        db.query(m.RepresentmentDraft)
        .filter(m.RepresentmentDraft.dispute_case_id == case.id)
        .order_by(desc(m.RepresentmentDraft.created_at))
        .first()
    )
    timeline = (
        db.query(m.AuditEvent)
        .filter(m.AuditEvent.dispute_case_id == case.id)
        .order_by(m.AuditEvent.created_at.asc())
        .all()
    )
    actions = (
        db.query(m.CaseAction)
        .filter(m.CaseAction.dispute_case_id == case.id)
        .order_by(m.CaseAction.created_at.asc())
        .all()
    )
    base["features"] = snap.features_json if snap else {}
    base["featureSnapshot"] = snap.snapshot_json if snap else None
    base["trueCategory"] = label.true_category if label else None
    base["wouldWinIfContested"] = label.would_win_if_contested if label else None
    base["latentWinProb"] = _f(label.latent_win_prob) if label else None
    base["draft"] = None
    if draft:
        base["draft"] = {
            "templateVersion": draft.template_version,
            "status": draft.generation_status,
            "text": draft.draft_text,
            "citations": draft.citations_json,
            "grounded": draft.grounded,
        }
    base["timeline"] = [
        {
            "id": ev.id,
            "at": _iso(ev.created_at),
            "eventType": ev.event_type,
            "actor": ev.actor_type,
            "actorRef": ev.actor_reference,
            "beforeState": ev.before_state,
            "afterState": ev.after_state,
            "message": ev.message,
        }
        for ev in timeline
    ]
    base["auditTrailReference"] = case.id
    base["actionHistory"] = [
        {
            "id": str(a.id),
            "actionType": a.action_type,
            "executionStatus": a.execution_status,
            "actorType": a.actor_type,
            "createdAt": _iso(a.created_at),
        }
        for a in actions
    ]
    if label is None:
        base.update(recoveredAmount=None, falsePositiveCost=None, netValue=None, simulatedOutcome=None)
        return base
    would = bool(label.would_win_if_contested)
    amount = float(case.disputed_amount)
    contest = float(case.contest_cost)
    contested = bool(pol and pol.recommended_action == "prepare_representment_draft")
    settled = settle(
        {"wouldWinIfContested": would, "disputedAmount": amount, "contestCost": contest},
        contested,
    )
    base["recoveredAmount"] = settled["recovered"]
    base["falsePositiveCost"] = settled["fp"]
    base["netValue"] = settled["recovered"] - settled["contestCost"] - settled["fp"]
    if not contested:
        base["simulatedOutcome"] = (
            "not_contested" if pol and pol.recommended_action == "recommend_do_not_contest" else None
        )
    elif settled["win"]:
        base["simulatedOutcome"] = "won_simulated"
    else:
        base["simulatedOutcome"] = "lost_simulated"
    return base


def record_event(db: Session, case: m.DisputeCase, event: str, message: str,
                 actor: m.OperatorUser, *, before: str | None = None, metadata: dict | None = None) -> None:
    now = datetime.now(timezone.utc)
    ev = make_audit(case.id, event, message, at=now.isoformat())
    db.add(m.AuditEvent(
        id=ev["id"], dispute_case_id=case.id, event_type=event,
        actor_type="human", actor_reference=str(actor.id),
        before_state=before or case.state, after_state=case.state,
        message=message, metadata_json=metadata or {}, created_at=now,
    ))


def block_action(db: Session, case: m.DisputeCase, actor: m.OperatorUser,
                 reason: str, *, requested: str | None = None, status: int = 409) -> NoReturn:
    record_event(db, case, "action.blocked", reason, actor,
                 metadata={"requested": requested, "reason": reason})
    db.commit()
    raise HTTPException(status_code=status, detail={
        "reason": reason, "currentState": case.state, "requestedState": requested,
    })


def lock_case(db: Session, case_id: str) -> m.DisputeCase:
    case = (db.query(m.DisputeCase).filter(m.DisputeCase.id == case_id)
            .populate_existing().with_for_update().one_or_none())
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


def apply_action(db: Session, case: m.DisputeCase, action: str, actor: m.OperatorUser) -> m.DisputeCase:
    case = lock_case(db, case.id)
    if actor.role not in {"analyst", "reviewer", "admin"}:
        block_action(db, case, actor, "This staff role cannot act on cases.", status=403)
    try:
        nxt = target_state(action)
    except ValueError:
        block_action(db, case, actor, "Unknown case action.", status=422)
    if action == "close_case" and actor.role not in {"reviewer", "admin"}:
        block_action(db, case, actor, "Close requires reviewer or admin.", requested=nxt, status=403)

    pol = (
        db.query(m.PolicyDecision)
        .filter(m.PolicyDecision.dispute_case_id == case.id)
        .order_by(desc(m.PolicyDecision.created_at))
        .first()
    )
    if pol is None:
        block_action(db, case, actor, "No policy decision on file.", requested=nxt)
    draft = None
    package = None
    payload = None
    if action == "prepare_representment_draft":
        if case.state == "human_review" and actor.role not in {"reviewer", "admin"}:
            block_action(db, case, actor, "Only a reviewer or admin may approve a case from human review.", requested=nxt, status=403)
        payload = serialize_case(db, case, full=True)
        package = (db.query(m.EvidencePackage).filter(m.EvidencePackage.dispute_case_id == case.id)
                   .order_by(desc(m.EvidencePackage.created_at)).first())
        try:
            validate_draft_evidence(payload.get("evidencePackage") or {})
        except ValueError as exc:
            block_action(db, case, actor, str(exc), requested=nxt)
        if not (payload.get("featureSnapshot") or {}).get("transaction"):
            block_action(db, case, actor, "Transaction snapshot is unavailable.", requested=nxt)
        if not pol.allowed and case.state != "human_review":
            block_action(db, case, actor, "Policy has not allowed draft preparation.", requested=nxt)
        draft = (db.query(m.RepresentmentDraft).filter(m.RepresentmentDraft.dispute_case_id == case.id)
                 .order_by(desc(m.RepresentmentDraft.created_at)).first())
        if (case.state == "draft_ready" and pol.allowed and draft
                and draft.generation_status == "completed" and draft.evidence_package_id == package.id):
            return case

    if case.state == nxt:
        if action != "prepare_representment_draft":
            return case
    elif not can_transition(case.state, nxt):
        block_action(db, case, actor, "invalid_transition", requested=nxt)

    if action == "prepare_representment_draft" and case.state == "human_review":
        # Human approval is a new decision, preserving the original blocked
        # decision. A reviewer can accept model uncertainty, never absent proof.
        pol = m.PolicyDecision(
            dispute_case_id=case.id, policy_version=pol.policy_version,
            profile=pol.profile, allowed=True,
            recommended_action="prepare_representment_draft", fight_decision="contest_recommended",
            block_reasons_json=[], input_snapshot_hash=pol.input_snapshot_hash,
            rules_evaluated_json=[*pol.rules_evaluated_json, {
                "rule": "human_review_approval", "passed": True,
                "detail": "A reviewer approved preparation after mandatory evidence validation.",
            }], created_at=datetime.now(timezone.utc),
        )
        db.add(pol)
        db.flush()
        record_event(db, case, "policy.evaluated", "Reviewer approval recorded; mandatory evidence verified.", actor,
                     metadata={"policyDecisionId": str(pol.id)})

    if action == "prepare_representment_draft":
        generated = build_grounded_draft(
            raw={**payload, "merchant": {"name": payload["merchantName"]}},
            evidence=payload["evidencePackage"],
            policy={"allowed": True, "profile": pol.profile, "policyVersion": pol.policy_version},
        )
        db.add(m.RepresentmentDraft(
            dispute_case_id=case.id, evidence_package_id=package.id,
            template_version=generated["templateVersion"], draft_text=generated["text"],
            citations_json=generated["citations"], generation_status="completed", grounded=True,
            created_at=datetime.now(timezone.utc),
        ))
    db.add(
        m.CaseAction(
            dispute_case_id=case.id,
            policy_decision_id=pol.id,
            action_type=action,
            execution_status="completed",
            actor_type="human",
            result_json={"to": nxt},
        )
    )
    before = case.state
    case.state = nxt
    if nxt == "closed":
        case.closed_at = datetime.now(timezone.utc)
    event = {
        "prepare_representment_draft": "draft.generated",
        "request_human_review": "case.routed_to_review",
        "recommend_do_not_contest": "case.not_contested",
        "close_case": "case.closed",
        "mark_evidence_incomplete": "evidence.incomplete",
        "request_missing_evidence": "evidence.requested",
    }[action]
    record_event(db, case, event, f"Operator action: {action.replace('_', ' ')}.", actor,
                 before=before, metadata={"policyDecisionId": str(pol.id)})
    db.commit()
    db.refresh(case)
    return case
