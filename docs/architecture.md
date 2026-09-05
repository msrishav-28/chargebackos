# ChargebackOS Architecture Specification

This document describes the implemented architecture. See [quality review](quality_review.md) for verification limits and release gates.

## 1. Architecture Principles

1. **Policy before AI:** No machine-learning prediction or LLM output can directly cause an automatic case action. Every action passes through the deterministic Policy Engine.
2. **Evidence before Language:** The LLM may summarize or draft only from structured evidence gathered by the Evidence Assembler. It cannot invent facts.
3. **Evaluation as a First-Class Subsystem:** Training, test-set evaluation, calibration, threshold selection, and false-positive cost calculation are product capabilities, not offline afterthoughts.
4. **Case-Oriented Domain Model:** The `dispute_case` is the core domain aggregate. Events, predictions, evidence, and audit logs attach to it.
5. **Explicit State Transitions:** Every lifecycle change is validated by a state machine and emitted to the audit stream.

## 2. Logical Architecture

```text
+----------------+      +---------------------------+
| Dashboard UI   |<---->| Application API           |
| TanStack Start |      +-------------+-------------+
+-------+--------+                    |
        |                             v
        |                 +--------------------------+
        |                 | Dispute Ingestion        |
        |                 +-------------+------------+
        |                               |
        |                               v
        |                 +--------------------------+
        |                 | Dispute Case Service     |
        |                 +-------------+------------+
        |                               |
        |         +---------------------+---------------------+
        |         |                                           |
        |         v                                           v
        | +-----------------------+                 +------------------+
        | | Intelligence Service  |                 | Evidence Service |
        | | model + calibration   |                 | schemas + links  |
        | +-----------+-----------+                 +--------+---------+
        |             |                                      |
        |             +------------------+-------------------+
        |                                v
        |                    +-----------------------+
        |                    | Deterministic Policy  |
        |                    | Engine                |
        |                    +-----------+-----------+
        |                                |
        |         +----------------------+--------------------+
        |         |                      |                    |
        |         v                      v                    v
        |  +-------------+      +----------------+   +------------------+
        |  | Drafting    |      | Human Review   |   | Do Not Contest   |
        |  | Service     |      | Queue          |   | / Close          |
        |  +------+------+      +----------------+   +------------------+
        |         |
        |         v
        |  +-------------------+
        |  | Audit Service     |
        |  +---------+---------+
        |            |
        v            v
+------------------------------+
| PostgreSQL + jobs + metrics |
+------------------------------+
```

## 3. Recommended Stack

- **Dashboard:** TanStack Start (React 19), TypeScript, Tailwind CSS. Not Next.js — that website stack is locked.
- **Charts:** Recharts
- **API / Backend:** FastAPI, Python 3.11+, SQLAlchemy 2.0
- **Database:** PostgreSQL on Neon for JSONB evidence and relational integrity
- **ML:** scikit-learn HistGradientBoosting with isotonic calibration
- **Explainability:** approximate permutation Shapley values against a training-median reference
- **Jobs:** Postgres-backed runs inside FastAPI for this pass. Redis/Celery remain later.

## 4. State Machine Implementation

Allowed case transitions:
- `received` -> `normalized` -> `triaged`
- `triaged` -> `evidence_collecting`
- `evidence_collecting` -> `evidence_incomplete` OR `policy_review`
- `evidence_incomplete` -> `human_review`
- `policy_review` -> `draft_ready` OR `human_review` OR `not_contested`
- `draft_ready` -> `submitted_simulated`
- `submitted_simulated` -> `won_simulated` OR `lost_simulated`
- `won_simulated` / `lost_simulated` / `not_contested` -> `closed`

Invalid transitions emit an `action.blocked` audit event and return HTTP 409 without mutating the case.

Normalized cases without a compatible model or complete frozen snapshot route to human review with a blocked decision and no score. Triage may be retried when the model is available. Operational ingests must reference existing synthetic transactions; no transaction or outcome facts are invented.

The processing endpoints persist triage, evidence assembly and policy evaluation separately. Draft preparation remains a guarded action. Optional AI arranges existing verified paragraphs; the server accepts only a complete permutation of paragraph indexes, preserving facts and citations.

Evaluation jobs are Postgres rows executed inside FastAPI. A restart can interrupt execution. A new scheduling attempt marks jobs older than 30 minutes failed. The case book remains unchanged by evaluation. Simulated case outcomes are hypothetical projections, not realized recovery or filing.
