from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models as m
from app.core.logging import log_event
from app.db import SessionLocal
from app.domain.constants import DATASET_VERSION, POLICY_VERSION
from app.domain.model import load_model
from app.services.benchmark import benchmark


def queue_evaluation(db: Session, actor: m.OperatorUser, key: str | None) -> tuple[m.BatchRun, bool]:
    if key is not None and (not key.strip() or len(key) > 80):
        raise HTTPException(status_code=422, detail="Idempotency-Key must contain 1–80 characters.")
    # One row serializes scheduling across API processes; the job itself runs
    # outside this transaction and never edits the case book.
    profile = db.query(m.PolicyProfile).filter_by(id="balanced").with_for_update().one_or_none()
    if profile is None:
        raise HTTPException(status_code=409, detail="Prepare the synthetic benchmark before running evaluation.")
    stored_key = f"evaluation:{actor.id}:{key}" if key else None
    if stored_key:
        prior = db.get(m.IdempotencyKey, stored_key)
        if prior:
            run = db.get(m.BatchRun, UUID(prior.response_json["batchRunId"]))
            if run:
                return run, False
    latest = db.query(m.BatchRun).filter_by(state="completed").order_by(desc(m.BatchRun.started_at)).first()
    if latest is None:
        raise HTTPException(status_code=409, detail="Prepare the synthetic benchmark before running evaluation.")
    bundle = load_model()
    if bundle is None:
        raise HTTPException(status_code=503, detail="Model artifact unavailable. An operator must prepare the model before evaluation.")
    target = latest.config_json.get("n")
    if target != bundle.get("nCases") or latest.random_seed != 42 or latest.model_version != bundle["modelVersion"]:
        raise HTTPException(status_code=409, detail="The stored benchmark and installed model do not match. Evaluation cannot mix versions.")
    now = datetime.now(timezone.utc)
    active = db.query(m.BatchRun).filter(m.BatchRun.state.in_(["queued", "running"])).all()
    for run in active:
        started = run.started_at.replace(tzinfo=timezone.utc) if run.started_at.tzinfo is None else run.started_at
        if started > now - timedelta(minutes=30):
            raise HTTPException(status_code=409, detail="An evaluation is already running. Wait for it to finish.")
        run.state = "failed"
        run.completed_at = now
        run.summary_json = {"error": "Evaluation interrupted or exceeded its 30-minute lease."}
    run = m.BatchRun(id=uuid4(), scenario_name="default_v1", strategy="ml_policy", random_seed=42,
                     dataset_version=DATASET_VERSION, model_version=bundle["modelVersion"], policy_version=POLICY_VERSION,
                     state="queued", config_json={"seed": 42, "n": target}, summary_json={})
    db.add(run)
    if stored_key:
        db.add(m.IdempotencyKey(key=stored_key, response_json={"batchRunId": str(run.id)}))
    db.add(m.AuditEvent(id="ae-eval-" + uuid4().hex, event_type="evaluation.queued", actor_type="human",
                        actor_reference=str(actor.id), message="A frozen synthetic benchmark evaluation was queued.",
                        metadata_json={"batchRunId": str(run.id)}))
    db.commit()
    return run, True


def execute_evaluation(run_id: UUID) -> None:
    with SessionLocal() as db:
        run = db.get(m.BatchRun, run_id)
        if run is None or run.state != "queued":
            return
        run.state = "running"
        db.commit()
        try:
            bundle = load_model()
            if bundle is None or bundle["modelVersion"] != run.model_version:
                raise ValueError("Model unavailable or changed since scheduling")
            _, summary = benchmark(bundle, run.random_seed, run.config_json["n"])
            run.summary_json = summary
            run.state = "completed"
            run.completed_at = datetime.now(timezone.utc)
            ev = summary["evaluation"]
            ml = next(row for row in ev["strategies"] if row["strategy"] == "ml_policy")
            for name, value in {"net_value": ml["netValue"], "precision": ev["fightWorthiness"]["precision"],
                                "recall": ev["fightWorthiness"]["recall"]}.items():
                db.add(m.EvaluationMetric(batch_run_id=run.id, metric_name=name, metric_value=value))
            db.commit()
            log_event("evaluation.completed", batch_id=str(run.id), model_version=run.model_version)
        except Exception as exc:
            db.rollback()
            run = db.get(m.BatchRun, run_id)
            run.state = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.summary_json = {"error": "Evaluation failed. See the server log using this run identifier."}
            db.commit()
            log_event("evaluation.failed", batch_id=str(run_id), error_type=type(exc).__name__)
