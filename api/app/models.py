import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class OperatorUser(Base):
    __tablename__ = "operator_users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["OperatorSession"]] = relationship(back_populates="user")


class OperatorSession(Base):
    __tablename__ = "operator_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operator_users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[OperatorUser] = relationship(back_populates="sessions")


class PolicyProfile(Base):
    __tablename__ = "policy_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    min_confidence: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    min_win_probability: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    min_expected_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    true_fraud_default: Mapped[str] = mapped_column(String(32), nullable=False)
    max_auto_prep_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    segment: Mapped[str] = mapped_column(String(32), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    policy_profile_id: Mapped[str] = mapped_column(ForeignKey("policy_profiles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    account_age_days: Mapped[int] = mapped_column(nullable=False)
    prior_successful_orders: Mapped[int] = mapped_column(nullable=False)
    prior_disputes: Mapped[int] = mapped_column(nullable=False)
    prior_refunds: Mapped[int] = mapped_column(nullable=False)
    responsiveness_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    region_bucket: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    transaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authentication_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    device_consistency_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    location_consistency_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    billing_descriptor_recognized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payment_method_age_days: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    fulfillment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    order_confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refund_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DisputeCase(Base):
    __tablename__ = "dispute_cases"
    __table_args__ = (
        UniqueConstraint("external_dispute_id", name="uq_dispute_external_id"),
        Index("ix_dispute_merchant_state", "merchant_id", "state"),
        Index("ix_dispute_reason_opened", "reason_family", "opened_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    external_dispute_id: Mapped[str] = mapped_column(String(64), nullable=False)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_family: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_label: Mapped[str] = mapped_column(String(160), nullable=False)
    disputed_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    split: Mapped[str] = mapped_column(String(16), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    demo_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_label: Mapped[str] = mapped_column(String(160), nullable=False)
    contest_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SimulationLabel(Base):
    __tablename__ = "simulation_labels"

    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), primary_key=True)
    true_category: Mapped[str] = mapped_column(String(64), nullable=False)
    latent_win_prob: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    would_win_if_contested: Mapped[bool] = mapped_column(Boolean, nullable=False)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[uuid.UUID] = uuid_pk()
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(32), nullable=False)
    features_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    __table_args__ = (
        CheckConstraint("category_confidence >= 0 AND category_confidence <= 1", name="ck_pred_conf"),
        CheckConstraint("fight_worthiness_probability >= 0 AND fight_worthiness_probability <= 1", name="ck_pred_win"),
        Index("ix_pred_case_created", "dispute_case_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(32), nullable=False)
    predicted_category: Mapped[str] = mapped_column(String(64), nullable=False)
    category_confidence: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    fight_worthiness_probability: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    expected_recovered_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    shap_summary_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    raw_scores_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calibrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidencePackage(Base):
    __tablename__ = "evidence_packages"
    __table_args__ = (
        CheckConstraint("completeness_score >= 0 AND completeness_score <= 1", name="ck_ev_complete"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    reason_family: Mapped[str] = mapped_column(String(32), nullable=False)
    completeness_score: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    mandatory_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    missing_required_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    missing_preferred_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    package_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (Index("ix_ev_item_case_type", "dispute_case_id", "evidence_type"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_packages.id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[uuid.UUID] = uuid_pk()
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    profile: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(64), nullable=False)
    fight_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    block_reasons_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    rules_evaluated_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    input_snapshot_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RepresentmentDraft(Base):
    __tablename__ = "representment_drafts"

    id: Mapped[uuid.UUID] = uuid_pk()
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    evidence_package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_packages.id"), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    generation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseAction(Base):
    __tablename__ = "case_actions"

    id: Mapped[uuid.UUID] = uuid_pk()
    dispute_case_id: Mapped[str] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=False)
    policy_decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_decisions.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_case_created", "dispute_case_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    dispute_case_id: Mapped[str | None] = mapped_column(ForeignKey("dispute_cases.id", ondelete="CASCADE"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    before_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    after_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BatchRun(Base):
    __tablename__ = "batch_runs"
    __table_args__ = (Index("ix_batch_state_started", "state", "started_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    scenario_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    random_seed: Mapped[int] = mapped_column(nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"
    __table_args__ = (Index("ix_eval_run_name", "batch_run_id", "metric_name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batch_runs.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    slice_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slice_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
