# ChargebackOS — Agent instructions (locked)

**Single source of truth** for anyone (human or agent) working in this repository.

End goal: run ChargebackOS as a real hosted system. **Do not rewrite the website to Next.js.** The current website stack (TanStack Start) has no compatibility issue with FastAPI, Neon, or sign-in.

Product: **ChargebackOS** — defense-only chargeback triage for the Razorpay AI Buildathon, AI Risk Manager track. One loss class. Policy before AI. Evidence before language. Synthetic data only. No live money, no live bank filing, no customer contact.

---

## Locked stack

| Piece | Choice | Host |
| --- | --- | --- |
| Website | TanStack Start, React 19, Tailwind v4, `DESIGN.md` (“Column”) | Vercel |
| Server | FastAPI in `api/` | Render |
| Database | PostgreSQL | Neon (pooled `DATABASE_URL`; direct `DATABASE_URL_DIRECT` for Alembic) |
| Sign-in | Email + password on FastAPI; sessions in Neon | same Neon |
| Jobs | Postgres job rows inside FastAPI | Redis/Celery later, not this pass |

- The **Python server owns records and rules.** The website is an operator console. After sign-in, Overview / Disputes / case / Evaluation / Policies / About read FastAPI. Do not revive `getUniverse()` or `localStorage` as the live book.
- This pass uses a **Bearer token** in `sessionStorage` (`VITE_API_URL`). `vercel.app` and `onrender.com` cannot share cookies. A same-origin website proxy remains later if we want httpOnly cookies only.
- Judges may also curl Render `/api/v1/*` with a bearer token.
- Only FastAPI opens Neon. The website must not write product tables.
- Leftover Grok App Builder files may remain on disk. Do not teach agents to use the Grok broker, PGLite as the product DB, or `migrations/auth/` as the live schema. Do not delete those leftovers unless a later explicit YES says so.

### Website rules

1. Read `DESIGN.md` first. Do not invent tokens. No generic `bg-red-500` / `text-blue-600`.
2. Tone: high-trust risk-ops console (Brex/Stripe), not a playful landing page.
3. Routes stay: `/`, `/disputes`, `/disputes/$caseId`, `/evaluation`, `/policies`, `/about`, plus `/login`.
4. TanStack Query for server state. Strict TypeScript. Fail loudly.
5. Console routes require a session. Fail closed. Hiding a button is not security.

### Server rules

1. FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic. Schema in `api/` migrations is the source of truth for product and operator tables.
2. Deterministic policy engine outranks the model and any LLM. No action without a stored policy decision.
3. Invalid state transitions: HTTP 409, `action.blocked` audit event, **no write**.
4. Idempotent ingest on `external_dispute_id`.
5. Structured logs: request id, correlation id, case id, batch id, model version, policy version, timing, error type. Never log passwords.
6. If the model artifact is missing: fail closed to human review. Do not invent scores.
7. Health: `/health/live`, `/health/ready`, `/health/model`.
8. Free Render sleeps. The website must show “operations server is waking” with retry, not a blank dashboard. Demo script: open `/health/live` before presenting.

### Sign-in (no Clerk, no Supabase Auth in this pass)

Neon is Postgres only. FastAPI is the receptionist.

- `operator_users` — email, argon2 hash, role (`viewer` / `analyst` / `reviewer` / `admin`), active flag. Demo staff, not synthetic cardholders.
- `operator_sessions` — token hash, expiry, revoked_at.
- Synthetic `customers` never log in.
- `viewer` read. `analyst` allowed case actions except close/reset. `reviewer` can approve a draft from human review. `admin` reset demo and re-run evaluation. Policy thresholds are not editable in this submission.
- Seeded demo staff passwords live in env / secrets, never committed.

---

## Now vs later vs never

### This pass (must ship)

Real FastAPI APIs, Neon memory, email/password roles, audit + 409, evidence YAML, seed manifest, synthetic-data disclaimer, structured logs, waking/error UI, pytest for policy / evidence YAML / illegal transitions. Extra APIs: `GET /api/v1/disputes/{id}/timeline`, `GET /api/v1/evaluations`, `GET /api/v1/auth/me`. A Playwright login→demo→blocked path is **later** (skipped this pass).

Existing queue filters stay (merchant / reason / category / state / high-value / review).

### Later — still on the table (do not treat as forbidden forever)

We **can** have these. They are skipped **this pass**, not banned:

- **Redis and Celery** — the architecture doc lists them for background jobs. This pass stores jobs as Postgres rows because 1,500 synthetic cases do not need a second free Render service that also sleeps. Add them when batch volume or long jobs need a real queue.
- **15,000 extra undisputed transactions as the default seed** — the master spec’s ledger scale. Default seed is ~1,500 *disputes* so first seed stays minutes, not a tiny Neon stall. Optional later via a full-ledger flag.
- Extra queue filters (confidence / evidence completeness / policy result)
- Playwright login → CB-DEMO-01 / CB-DEMO-03 blocked-draft path
- Clerk, Supabase Auth, or Google login if email/password on Neon is no longer enough
- XGBoost/LightGBM **package** in place of scikit-learn HistGradientBoosting
- `expire_stale_cases` timed worker
- Client-recorded demo video
- Paying Render so it does not sleep

### Never for this product (not “later”)

- Rewriting the website to Next.js (TanStack Start on Vercel is official with Nitro)
- **Nagging customers, retrying cards, or dunning** — that is a *failed-payment recovery* product. ChargebackOS is *post-dispute merchant defense*. Do not add customer contact.
- Live chargeback filing, live money movement, refunds, or customer emails
- Payment-card testing, fraud evasion, or any offense-capable tool
- Dropping/resetting shared Neon without a new explicit YES
- Deleting leftover builder files without a new explicit YES
- Committing `.env` files with real secrets
- Installing Docker on a machine that already has Neon. Keep `docker-compose.yml` in the repo for other developers only.

---

## Domain invariants

- Frozen 70 / 15 / 15 split. Thresholds chosen on validation only. Dashboard metrics from held-out test.
- Four baselines: contest nothing, contest everything, rules only, ML + policy.
- False-positive cost is first-class. Net value = recovery − contest cost − FP penalty.
- LLM drafts only from structured evidence JSON. Cite evidence ids. Never invent facts. Never override policy.
- Simulation labels (`true_category`, would-win) live off the case row so the model cannot be fed the answer.
- Seed 42. Narrative cases `CB-DEMO-01` … `CB-DEMO-05` stay on the test split.

---

## Local workflow

Windows/macOS/Linux, not a Grok sandbox.

- API: `api/` — Python 3.11+, uvicorn, Alembic. Neon `DATABASE_URL` (pooled) required for real runs. Alembic uses `DATABASE_URL_DIRECT` when set.
- Web: `npm run dev` (port 8080). `VITE_API_URL` points at FastAPI. Sign-in uses a Bearer token this pass (two hosts cannot share cookies).
- Do not use PGLite as the product store. Do not use Render free Postgres.
- `docker-compose.yml` is optional for other people. Do not require Docker when Neon is available.
- Do not create `.grok` folders. Do not add FastAPI logic into website route handlers.

When UI changes: match `DESIGN.md`. When API changes: pytest. Do not leave stubs, TODOs, or a second source of truth.
