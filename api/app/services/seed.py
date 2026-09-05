from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db import Base, SessionLocal
from app.domain.constants import DATASET_VERSION, FEATURE_VERSION, MODEL_VERSION, POLICY_PROFILES, POLICY_VERSION
from app.services.benchmark import benchmark, seed_manifest
from app.domain.generate import generate_world
from app.domain.model import load_model, train_model
from app import models as m

MANIFEST_PATH = Path(__file__).resolve().parents[3] / "data" / "seed_manifest.json"


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def persist_scored(db: Session, scored: list[dict]) -> None:
    merchants = {c["merchant"]["id"]: c["merchant"] for c in scored}
    for mid, mer in merchants.items():
        if db.get(m.Merchant, mid):
            continue
        db.add(
            m.Merchant(
                id=mid,
                name=mer["name"],
                segment=mer["segment"],
                timezone=mer["timezone"],
                policy_profile_id=mer["policyProfile"],
            )
        )
    db.flush()
    for c in scored:
        if db.get(m.Customer, c["customerId"]):
            continue
        snap = c["featureSnapshot"]
        db.add(
            m.Customer(
                id=c["customerId"],
                merchant_id=c["merchant"]["id"],
                account_age_days=int(snap["customerHistory"]["accountAgeDays"]),
                prior_successful_orders=int(snap["customerHistory"]["priorSuccessfulOrders"]),
                prior_disputes=int(snap["customerHistory"]["priorDisputes"]),
                prior_refunds=int(snap["customerHistory"]["priorRefunds"]),
                responsiveness_score=0,
                region_bucket=snap["customerHistory"]["regionBucket"],
            )
        )
    db.flush()
    for c in scored:
        if db.get(m.Transaction, c["transactionId"]):
            continue
        snap = c["featureSnapshot"]
        db.add(
            m.Transaction(
                id=c["transactionId"],
                merchant_id=c["merchant"]["id"],
                customer_id=c["customerId"],
                amount=c["disputedAmount"],
                currency="INR",
                transaction_at=_dt(snap["transaction"]["transactionAt"]),
                authentication_completed=bool(snap["sessionAuth"]["authenticationCompleted"]),
                device_consistency_score=snap["sessionAuth"]["deviceConsistency"],
                location_consistency_score=snap["sessionAuth"]["locationConsistency"],
                billing_descriptor_recognized=bool(snap["transaction"]["billingDescriptorRecognized"]),
                payment_method_age_days=int(snap["transaction"]["paymentMethodAgeDays"]),
            )
        )
    db.flush()
    for c in scored:
        if db.get(m.Order, c["orderId"]):
            continue
        snap = c["featureSnapshot"]
        db.add(
            m.Order(
                id=c["orderId"],
                transaction_id=c["transactionId"],
                fulfillment_type=snap["fulfillment"]["type"],
                order_confirmed_at=_dt(snap["fulfillment"]["orderConfirmedAt"]),
                shipped_at=_dt(snap["transaction"]["transactionAt"]) if snap["fulfillment"]["shipped"] else None,
                delivered_at=_dt(snap["transaction"]["transactionAt"]) if snap["fulfillment"]["delivered"] else None,
                delivery_confirmed=bool(snap["fulfillment"]["delivered"]),
                refund_requested_at=_dt(snap["transaction"]["transactionAt"]) if snap["fulfillment"]["refundRequested"] else None,
                cancellation_requested_at=_dt(snap["transaction"]["transactionAt"]) if snap["fulfillment"]["cancellationRequested"] else None,
            )
        )
    db.flush()
    for c in scored:
        if db.get(m.DisputeCase, c["id"]):
            continue
        db.add(
            m.DisputeCase(
                id=c["id"],
                external_dispute_id=c["externalDisputeId"],
                merchant_id=c["merchant"]["id"],
                customer_id=c["customerId"],
                transaction_id=c["transactionId"],
                order_id=c["orderId"],
                reason_code=c["reasonCode"],
                reason_family=c["reasonFamily"],
                reason_label=c["reasonLabel"],
                disputed_amount=c["disputedAmount"],
                currency="INR",
                state=c["state"],
                split=c["split"],
                is_demo=c["isDemo"],
                demo_role=c.get("demoRole"),
                customer_label=c["customerLabel"],
                contest_cost=c["contestCost"],
                opened_at=_dt(c["openedAt"]),
            )
        )
        db.add(
            m.SimulationLabel(
                dispute_case_id=c["id"],
                true_category=c["trueCategory"],
                latent_win_prob=c["latentWinProb"],
                would_win_if_contested=c["wouldWinIfContested"],
            )
        )
        db.add(
            m.FeatureSnapshot(
                dispute_case_id=c["id"],
                feature_version=FEATURE_VERSION,
                features_json=c["features"],
                snapshot_json=c["featureSnapshot"],
            )
        )
        pred = c["prediction"]
        db.add(
            m.ModelPrediction(
                dispute_case_id=c["id"],
                model_version=pred["modelVersion"],
                feature_version=pred["featureVersion"],
                predicted_category=pred["predictedCategory"],
                category_confidence=pred["categoryConfidence"],
                fight_worthiness_probability=pred["fightWorthinessProbability"],
                expected_recovered_value=pred["expectedRecoveredValue"],
                shap_summary_json=pred["shap"],
                raw_scores_json=pred["classScores"],
                calibrated=True,
            )
        )
        pkg = c["evidencePackage"]
        package = m.EvidencePackage(
            dispute_case_id=c["id"],
            reason_family=pkg["reasonFamily"],
            completeness_score=pkg["completenessScore"],
            mandatory_complete=pkg["mandatoryComplete"],
            missing_required_json=pkg["missingRequired"],
            missing_preferred_json=pkg["missingPreferred"],
            package_hash=pkg["packageHash"],
        )
        db.add(package)
        db.flush()
        for item in pkg["items"]:
            db.add(
                m.EvidenceItem(
                    id=item["id"],
                    dispute_case_id=c["id"],
                    package_id=package.id,
                    evidence_type=item["type"],
                    evidence_key=item["key"],
                    label=item["label"],
                    tier=item["tier"],
                    present=item["present"],
                    is_required=item["tier"] == "required",
                    source_system=item["sourceSystem"],
                    source_reference=item["sourceReference"],
                    value_json={"summary": item["summary"], "value": item["value"]},
                )
            )
        pol = c["policyDecision"]
        decision = m.PolicyDecision(
            dispute_case_id=c["id"],
            policy_version=pol["policyVersion"],
            profile=pol["profile"],
            allowed=pol["allowed"],
            recommended_action=pol["recommendedAction"],
            fight_decision=pol["fightDecision"],
            block_reasons_json=pol["blockReasons"],
            rules_evaluated_json=pol["rulesEvaluated"],
            input_snapshot_hash=pol["inputSnapshotHash"],
        )
        db.add(decision)
        db.flush()
        db.add(
            m.RepresentmentDraft(
                dispute_case_id=c["id"],
                evidence_package_id=package.id,
                template_version=c["draft"]["templateVersion"],
                draft_text=c["draft"]["text"],
                citations_json=c["draft"]["citations"],
                generation_status=c["draft"]["status"],
                grounded=c["draft"]["grounded"],
            )
        )
        for ev in c["timeline"]:
            db.add(
                m.AuditEvent(
                    id=ev["id"][:120],
                    dispute_case_id=c["id"],
                    event_type=ev["eventType"],
                    actor_type=ev["actor"],
                    actor_reference=ev.get("actorRef"),
                    before_state=ev.get("beforeState"),
                    after_state=ev.get("afterState"),
                    message=ev["message"],
                    metadata_json={},
                    created_at=_dt(ev["at"]) if ev.get("at") else datetime.now(timezone.utc),
                )
            )


def seed_operators(db: Session) -> None:
    settings = get_settings()
    if len(settings.demo_password) < 12 or settings.demo_password.startswith("change-me"):
        raise ValueError("Set a unique DEMO_PASSWORD of at least 12 characters before preparing staff accounts.")
    password = hash_password(settings.demo_password)
    staff = [
        ("analyst@chargebackos.demo", "analyst", "Demo Analyst"),
        ("viewer@chargebackos.demo", "viewer", "Demo Viewer"),
        ("reviewer@chargebackos.demo", "reviewer", "Demo Reviewer"),
        ("admin@chargebackos.demo", "admin", "Demo Admin"),
    ]
    for email, role, name in staff:
        existing = db.query(m.OperatorUser).filter(m.OperatorUser.email == email).one_or_none()
        if existing:
            continue
        db.add(m.OperatorUser(email=email, password_hash=password, role=role, display_name=name, active=True))


def seed_profiles(db: Session) -> None:
    for pid, p in POLICY_PROFILES.items():
        if db.get(m.PolicyProfile, pid):
            continue
        db.add(
            m.PolicyProfile(
                id=pid,
                label=p["label"],
                description=p["description"],
                min_confidence=p["minConfidence"],
                min_win_probability=p["minWinProbability"],
                min_expected_value=p["minExpectedValue"],
                true_fraud_default=p["trueFraudDefault"],
                max_auto_prep_rate=p["maxAutoPrepRate"],
                policy_version=POLICY_VERSION,
            )
        )


def run_seed(*, reset: bool = False) -> dict:
    settings = get_settings()
    db = SessionLocal()
    try:
        if reset:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name.startswith("operator_"):
                    continue
                db.execute(table.delete())
        seed_profiles(db)
        seed_operators(db)
        db.flush()
        if db.query(m.DisputeCase).count() > 0 and not reset:
            count = db.query(m.DisputeCase).count()
            if not db.query(m.BatchRun).filter_by(state="completed").first():
                raise ValueError("Existing cases have no completed seed manifest. Inspect the book before trying a reset.")
            db.commit()
            return {"ok": True, "skipped": True, "cases": count}
        world = generate_world(settings.seed, settings.dispute_target)
        bundle = load_model()
        if bundle is None or bundle.get("nCases") != settings.dispute_target:
            bundle = train_model(world["cases"])
        scored, summary = benchmark(bundle, settings.seed, settings.dispute_target)
        persist_scored(db, scored)
        ev = summary["evaluation"]
        run = m.BatchRun(
            scenario_name="default_v1", strategy="ml_policy", random_seed=settings.seed,
            dataset_version=DATASET_VERSION, model_version=MODEL_VERSION, policy_version=POLICY_VERSION,
            state="completed", completed_at=datetime.now(timezone.utc),
            config_json={"seed": settings.seed, "n": len(scored)}, summary_json=summary,
        )
        db.add(run)
        db.flush()
        ml = next(s for s in ev["strategies"] if s["strategy"] == "ml_policy")
        db.add(m.EvaluationMetric(batch_run_id=run.id, metric_name="net_value", metric_value=ml["netValue"]))
        db.add(m.EvaluationMetric(batch_run_id=run.id, metric_name="precision", metric_value=ev["fightWorthiness"]["precision"]))
        db.add(m.EvaluationMetric(batch_run_id=run.id, metric_name="recall", metric_value=ev["fightWorthiness"]["recall"]))
        db.commit()
        manifest = seed_manifest(scored, settings.seed)
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {"ok": True, "skipped": False, **manifest}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
