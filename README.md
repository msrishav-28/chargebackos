# ChargebackOS

**An AI-assisted, policy-controlled chargeback triage and evidence-response system.**

ChargebackOS is being developed for the **PayPal AI Hackathon** from an existing chargeback-triage prototype. PayPal sandbox integration is planned and is not yet implemented; see the [execution playbook](docs/execution-playbook.md). It focuses on a single, high-impact loss class—merchant chargebacks and friendly fraud—and provides a measurable, verifiable, and economically honest way to decide which disputes to contest.

The playbook defines 23 ordered tasks, implementation contracts, migration/recovery procedures, 26 acceptance gates, and the submission schedule. It distinguishes current behavior from planned functionality.

## Why Chargebacks?
Chargeback processing is document-heavy and operationally painful. Modern dispute automation relies on gathering transaction, delivery, communication, and authentication evidence. ChargebackOS differentiates itself through rigorous threshold economics, model calibration, an honest failure gallery, and a highly reviewable audit trail rather than generic LLM wrapper behavior.

## Defense-Only Statement
This system is purpose-built for merchant defense. It performs risk triage, evidence organization, policy-controlled response preparation, and review routing. **It does not create payment fraud methods, evasion flows, offensive testing tools, or unauthorized targeting capabilities.**

## Architecture
The system employs a strict "Policy before AI" and "Evidence before Language" architecture. AI models (tabular gradient boosting) and LLMs (for drafting) are never allowed to bypass deterministic merchant policies or invent missing evidence.

**Target stack:** TanStack Start website on Vercel, FastAPI server on Render, PostgreSQL on Supabase. The website is not Next.js; that stack is compatible and will not be rewritten. See `AGENTS.md`.

Please see the [Architecture Document](docs/architecture.md) for diagrams, the data model, and state machine specifications.

## Dataset Disclaimer
Real chargeback records are highly sensitive. This project relies on a deterministic synthetic generator designed around realistic operational relationships. The simulated dataset produces merchant profiles, transactions, authentication signals, and fulfillment records to evaluate the model without exposing real PII or financial data. See the [Data Dictionary](docs/data_dictionary.md) for schema details.

## Evaluation Protocol & Held-Out Metrics
ChargebackOS does not rely on "vibe checks." It is evaluated against a frozen, 15% held-out test set to measure:
- Precision, recall, and F1 across dispute categories.
- Expected recovered value vs. handling cost.
- See the full [Evaluation Protocol](docs/evaluation_protocol.md).

### Honest False-Positive Cost Assumptions
A model decision to contest a case is not free. Our evaluation penalizes false positives by calculating:
`expected_value = p_win × disputed_amount - contest_cost - expected_false_positive_penalty`
We provide a decision-threshold chart plotting precision, recall, and total expected net value.

## Known Limitations & Failure Gallery
The Evaluation page exposes misclassified cases, their strongest measured model contributions, and the resulting [Policy Engine](docs/policy_engine.md) decisions. Contributions describe model behavior; they do not prove the cause of an error or guarantee a safe outcome. See also [synthetic data disclaimer](docs/synthetic_data_disclaimer.md).

## Getting Started

You need Python 3.11+, Node.js 24 for the repository checks, and a Postgres URL. Use **Supabase PostgreSQL**. `docker-compose.yml` is optional for other developers who want Postgres on their own machine — it is not required here.

Hosted shape: [Hosting](docs/hosting.md) (Vercel + Render + Supabase).

### 1. API
```bash
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
# set DATABASE_URL (Supabase Session pooler), DATABASE_URL_DIRECT (direct or Session pooler), AUTH_SECRET, DEMO_PASSWORD
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Website
```bash
npm ci
# set VITE_API_URL=http://127.0.0.1:8000 in .env
npm run dev
```

Sign in as `analyst@chargebackos.demo` with `DEMO_PASSWORD`. Before a hosted pitch, open the Render `/health/live` URL once so the free server is awake.

Start here if you are a **judge or a hiring manager:** [Visitor guide](docs/visitor_guide.md) (uses the screenshots in `screenshots/`).

## Documentation Directory
- [Visitor guide (judges / portfolio)](docs/visitor_guide.md)
- [Hosting](docs/hosting.md)
- [Architecture & DB Schema](docs/architecture.md)
- [Policy Engine Rules](docs/policy_engine.md)
- [Model Card](docs/model_card.md)
- [Evaluation Protocol](docs/evaluation_protocol.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Threat Model](docs/threat_model.md)
- [Demo Script](docs/demo_script.md)
- [Synthetic data disclaimer](docs/synthetic_data_disclaimer.md)

---
*PayPal submission work is tracked in [the delivery plan](docs/shipping-plan.md).*

## Verification and measured limits

See the [quality review](docs/quality_review.md) for the local checks and release gates. No hosted database was changed by that review.

- Website: `npm run typecheck`, `npm run lint`, `npm run build`, and `node --experimental-strip-types --test src/lib/ops-schemas.test.ts`.
- API: from `api/`, run `python -m pytest -q`. Behavior tests use an in-memory SQLite adapter. The API-to-website contract test requires Node and installed website dependencies. These tests do not certify PostgreSQL locking or hosted behavior.
- Offline model: from `api/`, run `python -m app.train`. This does not open a database. It writes the ignored artifact and [measured report](api/ml/reports/benchmark.json). `--evaluate-only` reuses a matching artifact.

The default split is exactly 1,050 / 225 / 225. Rules-only currently leads ML + policy on simulated net value. Do not present a proven improvement over rules.

The operator console reads FastAPI only. The old in-browser fake book has been removed. Case buttons follow allowed server moves: a “draft ready” case can confirm a draft; route / do-not-contest / close stay disabled there.

Before sharing a live demonstration, resolve the [model artifact release gate](docs/hosting.md#model-artifact-release-gate) and check hosted sign-in and blocked drafting. The Render build trains the model; database initialization is a separate operation documented in the hosting guide. This repository is not submission-ready until those hosted checks pass.
