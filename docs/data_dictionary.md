# Data Dictionary & Database Schema

ChargebackOS uses PostgreSQL on **Neon**. The FastAPI app in `api/` owns the schema (Alembic). JSONB is used for evidence payloads, audit metadata, and policy rule snapshots. Case ids in this pass are stable text keys (`CB-DEMO-01`); operator ids are UUIDs.

Staff sign-in lives in `operator_users` and `operator_sessions` (not Clerk, not Supabase Auth). Synthetic `customers` never log in.

## Core Aggregates

### 1. `dispute_cases`
The central domain aggregate.
- `id` (text PK, e.g. `CB-DEMO-01`)
- `external_dispute_id` (varchar, unique)
- `merchant_id`, `customer_id`, `transaction_id`, `order_id` (text FKs)
- `reason_code` (varchar) & `reason_family` (varchar: unauthorized, not_received, service_issue, other)
- `disputed_amount` (numeric) & `currency` (char)
- `state` (varchar lifecycle state validated by the application)
- `opened_at`, `closed_at` (timestamptz)

### 2. `model_predictions`
Immutable prediction records tied to a specific model version.
- `dispute_case_id` (text FK)
- `model_version`, `feature_version` (varchar)
- `predicted_category` (enum)
- `category_confidence`, `fight_worthiness_probability` (numeric, 0-1 calibrated)
- `expected_recovered_value` (numeric)
- `shap_summary_json` (jsonb)

### 3. `evidence_items` & `evidence_packages`
Structured evidence linked to the case.
- `evidence_type` (enum: transaction, delivery, authentication, communication)
- `evidence_key` (varchar)
- `value_json` (jsonb)
- `is_required` (boolean)
- `completeness_score` (numeric, on the package level)
- `mandatory_complete` (boolean, on the package level)

### 4. `policy_decisions`
Deterministic rule evaluations.
- `dispute_case_id` (text FK)
- `policy_version` (varchar)
- `allowed` (boolean)
- `recommended_action` (enum)
- `block_reasons_json` (jsonb)
- `input_snapshot_hash` (varchar, for reproducibility)

### 5. `representment_drafts`
Versioned evidence-grounded paragraphs, with optional AI arrangement that preserves their facts.
- `dispute_case_id` (text FK), `evidence_package_id` (UUID FK)
- `draft_text` (text)
- `citations_json` (jsonb)
- `generation_status` (enum)

### 6. `audit_events`
The immutable timeline of everything that happens to a case.
- `dispute_case_id` (text FK)
- `event_type` (enum)
- `actor_type` (enum: system, human, model, policy)
- `before_state`, `after_state` (varchar)
- `message` (text)
- `metadata_json` (jsonb)

## Transaction & Customer Features
The dataset includes synthetic `transactions`, `orders`, and `customers` tables which provide the feature snapshots (e.g., `account_age_days`, `delivery_confirmed`, `authentication_completed`) required for ML inference.

## Operator tables
- `operator_users` — email, argon2 hash, role (`viewer` / `analyst` / `reviewer` / `admin`)
- `operator_sessions` — token hash, expiry, revoked_at

Simulation labels (`true_category`, would-win) live in `simulation_labels`, not on the case row.

## Processing records

`feature_snapshots` contains features and their source snapshot. The internal `evidenceSourceCaseId` records provenance when an operational ingest references a previously stored transaction. Operational ingests have `split=operational` and receive no invented simulation label.

`batch_runs` stores evaluation status, configuration and summary; `evaluation_metrics` stores numeric results. `idempotency_keys` connects repeated scheduling requests to one run. Policy input hashes cover economics, evidence, state and the rate cap. Evidence hashes include content and references.

Actual types and constraints remain in `api/app/models.py` and the existing Alembic revision. No table structure was changed during this review. The enum-like values described above are application vocabularies, not PostgreSQL enum types.
