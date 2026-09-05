from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models as m
from app.core.config import get_settings
from app.core.logging import RequestLogMiddleware, log_event
from app.core.security import hash_token, new_session_token, session_expiry, verify_password
from app.db import get_db
from app.domain.constants import EVIDENCE_SCHEMAS, FEATURE_VERSION, MODEL_VERSION, POLICY_PROFILES, POLICY_VERSION
from app.domain.model import load_model
from app.services.cases import apply_action, serialize_case, serialize_cases
from app.services.drafts import rewrite_grounded_draft
from app.services.seed import run_seed
from app.services.evaluations import queue_evaluation, execute_evaluation
from app.services.processing import IngestBody, ingest_case, triage_case, assemble_evidence, evaluate_case

ROLES_WRITE = {"analyst", "reviewer", "admin"}
ROLES_ADMIN = {"admin"}

app = FastAPI(title="ChargebackOS API", version="1.0.0")
settings = get_settings()
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class ActionBody(BaseModel):
    action: Literal[
        "prepare_representment_draft", "request_human_review",
        "mark_evidence_incomplete", "recommend_do_not_contest",
        "request_missing_evidence", "close_case",
    ]


class ResetBody(BaseModel):
    confirmation: Literal["REPLACE_SYNTHETIC_CASES"]


def current_user(
    db: Session = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
) -> m.OperatorUser:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in.")
    row = (
        db.query(m.OperatorSession)
        .filter(m.OperatorSession.token_hash == hash_token(token), m.OperatorSession.revoked_at.is_(None))
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=401, detail="Session expired.")
    expiry = row.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired.")
    user = db.get(m.OperatorUser, row.user_id)
    if user is None or not user.active or user.role not in {"viewer", "analyst", "reviewer", "admin"}:
        raise HTTPException(status_code=401, detail="Account disabled.")
    return user


def require_user(
    db: Session = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
) -> m.OperatorUser:
    return current_user(db, authorization)


@app.get("/health/live")
def health_live():
    return {"ok": True}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db.query(m.PolicyProfile).count()
    except SQLAlchemyError as exc:
        log_event("health.database_unavailable", error_type=type(exc).__name__)
        raise HTTPException(status_code=503, detail="Operations database is unavailable or not initialized.") from exc
    return {"ok": True, "database": True}


@app.get("/health/model")
def health_model(response: Response):
    bundle = load_model()
    if bundle is None:
        response.status_code = 503
    return {"ok": bundle is not None, "modelVersion": MODEL_VERSION if bundle else None}


@app.post("/api/v1/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    if len(settings.auth_secret) < 32 or settings.auth_secret.startswith("change-me"):
        raise HTTPException(status_code=503, detail="Staff sign-in has not been configured by the operator.")
    user = db.query(m.OperatorUser).filter(m.OperatorUser.email == body.email.strip().lower()).one_or_none()
    if user is None or not user.active or user.role not in {"viewer", "analyst", "reviewer", "admin"} or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = new_session_token()
    db.add(m.OperatorSession(user_id=user.id, token_hash=hash_token(token), expires_at=session_expiry()))
    db.commit()
    return {"token": token, "user": {"email": user.email, "role": user.role, "displayName": user.display_name}}


@app.post("/api/v1/auth/logout")
def logout(
    db: Session = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        row = db.query(m.OperatorSession).filter(m.OperatorSession.token_hash == hash_token(token)).one_or_none()
        if row:
            row.revoked_at = datetime.now(timezone.utc)
            db.commit()
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(user: m.OperatorUser = Depends(require_user)):
    return {"email": user.email, "role": user.role, "displayName": user.display_name}


@app.get("/api/v1/policies")
def policies(user: m.OperatorUser = Depends(require_user)):
    return {"policyVersion": POLICY_VERSION, "profiles": list(POLICY_PROFILES.values()), "evidenceSchemas": EVIDENCE_SCHEMAS}


@app.get("/api/v1/overview")
def overview(db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    run = db.query(m.BatchRun).filter(m.BatchRun.state == "completed").order_by(desc(m.BatchRun.started_at)).first()
    total = db.query(m.DisputeCase).count()
    queue_counts = {
        "total": total,
        "draftReady": db.query(m.DisputeCase).filter(m.DisputeCase.state == "draft_ready").count(),
        "humanReview": db.query(m.DisputeCase).filter(m.DisputeCase.state.in_(["human_review", "evidence_incomplete"])).count(),
        "notContested": db.query(m.DisputeCase).filter(m.DisputeCase.state == "not_contested").count(),
    }
    merchants = [{"id": x.id, "name": x.name, "segment": x.segment, "policyProfile": x.policy_profile_id} for x in db.query(m.Merchant).all()]
    if run is None:
        return {
            "overview": None,
            "evaluation": None,
            "failureGallery": [],
            "costAssumptions": None,
            "merchants": merchants,
            "queueCounts": queue_counts,
            "modelVersion": MODEL_VERSION,
            "policyVersion": POLICY_VERSION,
            "featureVersion": FEATURE_VERSION,
            "seed": settings.seed,
            "datasetVersion": None,
        }
    summary = run.summary_json or {}
    return {
        "overview": summary.get("overview"),
        "evaluation": summary.get("evaluation"),
        "failureGallery": summary.get("failureGallery") or [],
        "costAssumptions": summary.get("costAssumptions"),
        "merchants": merchants,
        "queueCounts": queue_counts,
        "modelVersion": run.model_version,
        "policyVersion": run.policy_version,
        "featureVersion": FEATURE_VERSION,
        "seed": run.random_seed,
        "datasetVersion": run.dataset_version,
    }


@app.get("/api/v1/disputes")
def list_disputes(
    db: Session = Depends(get_db),
    user: m.OperatorUser = Depends(require_user),
    state: str | None = None,
    merchant_id: str | None = None,
    reason_family: str | None = None,
    category: str | None = None,
    q: str | None = None,
    review: bool = False,
    high: bool = False,
    is_demo: bool | None = None,
    blocked: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(80, ge=1, le=200),
):
    query = db.query(m.DisputeCase)
    if state:
        query = query.filter(m.DisputeCase.state == state)
    if merchant_id:
        query = query.filter(m.DisputeCase.merchant_id == merchant_id)
    if reason_family:
        query = query.filter(m.DisputeCase.reason_family == reason_family)
    if review:
        query = query.filter(m.DisputeCase.state.in_(["human_review", "evidence_incomplete"]))
    if high:
        query = query.filter(m.DisputeCase.disputed_amount >= 10000)
    if is_demo is True:
        query = query.filter(m.DisputeCase.is_demo.is_(True))
    if blocked is not None:
        latest_allowed = (db.query(m.PolicyDecision.allowed)
                          .filter(m.PolicyDecision.dispute_case_id == m.DisputeCase.id)
                          .order_by(desc(m.PolicyDecision.created_at), desc(m.PolicyDecision.id))
                          .limit(1).correlate(m.DisputeCase).scalar_subquery())
        query = query.filter(latest_allowed.is_(not blocked))
    if category:
        latest_category = (db.query(m.ModelPrediction.predicted_category)
                           .filter(m.ModelPrediction.dispute_case_id == m.DisputeCase.id)
                           .order_by(desc(m.ModelPrediction.created_at), desc(m.ModelPrediction.id))
                           .limit(1).correlate(m.DisputeCase).scalar_subquery())
        query = query.filter(latest_category == category)
    if q:
        like = f"%{q}%"
        query = query.outerjoin(m.Merchant, m.Merchant.id == m.DisputeCase.merchant_id).filter(
            or_(
                m.DisputeCase.id.ilike(like),
                m.DisputeCase.reason_code.ilike(like),
                m.DisputeCase.reason_label.ilike(like),
                m.Merchant.name.ilike(like),
            )
        )
    total = query.count()
    rows = query.order_by(desc(m.DisputeCase.opened_at), m.DisputeCase.id).offset((page - 1) * limit).limit(limit).all()
    return {"items": serialize_cases(db, rows), "total": total, "page": page, "limit": limit}


@app.get("/api/v1/disputes/{case_id}")
def get_dispute(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    case = db.get(m.DisputeCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return serialize_case(db, case, full=True, actor=user)


@app.get("/api/v1/disputes/{case_id}/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    case = db.get(m.DisputeCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return serialize_case(db, case, full=True)["timeline"]


@app.post("/api/v1/disputes/{case_id}/prepare-draft")
def prepare_draft(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    case = _case(db, case_id)
    apply_action(db, case, "prepare_representment_draft", user)
    return serialize_case(db, case, full=True, actor=user)


@app.post("/api/v1/disputes/{case_id}/route-human-review")
def route_review(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    case = _case(db, case_id)
    apply_action(db, case, "request_human_review", user)
    return serialize_case(db, case, full=True, actor=user)


@app.post("/api/v1/disputes/{case_id}/action")
def case_action(case_id: str, body: ActionBody, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    if body.action == "close_case" and user.role not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Forbidden.")
    _require_write(user)
    case = _case(db, case_id)
    apply_action(db, case, body.action, user)
    return serialize_case(db, case, full=True, actor=user)


@app.post("/api/v1/disputes/{case_id}/rewrite-draft")
def rewrite_draft(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    return rewrite_grounded_draft(db, case_id, user, settings.xai_api_key)



@app.post("/api/v1/disputes/ingest", status_code=201)
def ingest(body: IngestBody, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    case = ingest_case(db, body, user)
    return serialize_case(db, case, full=True, actor=user)


@app.post("/api/v1/disputes/{case_id}/triage")
def triage(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    return serialize_case(db, triage_case(db, case_id, user), full=True, actor=user)


@app.post("/api/v1/disputes/{case_id}/assemble-evidence")
def evidence(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    return serialize_case(db, assemble_evidence(db, case_id, user), full=True, actor=user)


@app.post("/api/v1/disputes/{case_id}/evaluate-policy")
def policy_evaluation(case_id: str, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    _require_write(user)
    return serialize_case(db, evaluate_case(db, case_id, user), full=True, actor=user)


@app.post("/api/v1/evaluations/run", status_code=202)
def run_eval(background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user),
             idempotency_key: Annotated[str | None, Header()] = None):
    if user.role not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Admin only.")
    run, created = queue_evaluation(db, user, idempotency_key)
    response = {"batchRunId": str(run.id), "state": run.state}
    if created:
        background_tasks.add_task(execute_evaluation, run.id)
    return response


@app.get("/api/v1/evaluations")
def list_eval(limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    rows = db.query(m.BatchRun).order_by(desc(m.BatchRun.started_at), desc(m.BatchRun.id)).limit(limit).all()
    return {
        "items": [
            {"id": str(r.id), "strategy": r.strategy, "state": r.state, "startedAt": r.started_at.isoformat() if r.started_at else None, "seed": r.random_seed}
            for r in rows
        ]
    }


@app.get("/api/v1/evaluations/{batch_run_id}")
def get_eval(batch_run_id: UUID, db: Session = Depends(get_db), user: m.OperatorUser = Depends(require_user)):
    run = db.get(m.BatchRun, batch_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return {"id": str(run.id), "state": run.state, "summary": run.summary_json}


@app.post("/api/v1/demo/reset")
def reset_demo(body: ResetBody, user: m.OperatorUser = Depends(require_user)):
    if user.role not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Admin only.")
    return run_seed(reset=True)


@app.post("/api/v1/demo/seed")
def seed_demo(user: m.OperatorUser = Depends(require_user)):
    if user.role not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Admin only.")
    return run_seed(reset=False)


def _require_write(user: m.OperatorUser) -> None:
    if user.role not in ROLES_WRITE:
        raise HTTPException(status_code=403, detail="Forbidden.")


def _case(db: Session, case_id: str) -> m.DisputeCase:
    case = db.get(m.DisputeCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case
