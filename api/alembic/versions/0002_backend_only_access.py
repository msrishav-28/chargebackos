"""Protect backend-owned tables from Supabase browser roles.

Revision ID: 0002_backend_only_access
Revises: 0001_initial
"""

from alembic import op

revision = "0002_backend_only_access"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

# Frozen list: migrations must not pick up future application tables implicitly.
TABLES = (
    "operator_users", "operator_sessions", "policy_profiles", "merchants",
    "customers", "transactions", "orders", "dispute_cases", "simulation_labels",
    "feature_snapshots", "model_predictions", "evidence_packages", "evidence_items",
    "policy_decisions", "representment_drafts", "case_actions", "audit_events",
    "batch_runs", "evaluation_metrics", "idempotency_keys", "alembic_version",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL ON TABLE public."{table}" FROM PUBLIC')
        # Ordinary Postgres installations do not have these Supabase roles.
        for role in ("anon", "authenticated"):
            op.execute(f"""
                DO $$ BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                        REVOKE ALL ON TABLE public."{table}" FROM {role};
                    END IF;
                END $$;
            """)


def downgrade() -> None:
    # Do not silently expose password hashes or records during a rollback.
    # Leaving additive security in place is intentional.
    pass
