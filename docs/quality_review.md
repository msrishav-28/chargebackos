# Quality review — 2026-09-05

## Project map

ChargebackOS helps staff decide whether a synthetic merchant dispute is worth defending. It collects available proof, measures the likely outcome, applies fixed merchant rules, and prepares a cited response only when those controls allow it. It never files a bank dispute, moves money or contacts a customer.

The moving parts are an operator website, a Python operations server, a PostgreSQL record store, and local model training. Evaluation jobs run inside the server and keep their status in the database. There is no separate email, mobile or customer sign-in application.

The review read the three attachment specifications in the requested order, followed by AGENTS.md and DESIGN.md. It surveyed the repository layout, package and Python requirements, website and server entrypoints, database models and Alembic history, authentication and roles, policy/evidence/model code, shared utilities and their older browser twins, tests, scripts, environment samples, Docker/Render/Vercel configuration, and every documentation file. No repository CI workflow was found. Live credential values were not printed.

Healthy foundations: one server owns records, the model has a frozen split, evidence rules are explicit, and the product excludes live payment actions. The main defects were permissive case controls, incomplete processing/evaluation routes, unsafe response assumptions in the website, and misleading model/evaluation claims.

The local sign-in and case-control repairs were explicitly approved in this conversation. A later approved cleanup removed the unused in-browser fake book, unused UI packages, and the dead `_family` helper. No shared records, staff passwords, database structure, hosting settings, official history, attachments or design instructions were changed.

## Work performed

- Sign-in rejects inactive staff, invalid roles and malformed stored password hashes. Every API permission check remains on the server.
- Case actions require stored policy, valid state and the right role. Mandatory missing evidence blocks every draft, including reviewer approval. Refused actions leave an audit record; successful retries do not duplicate drafts.
- Ingest verifies stored transaction references and handles repeated external identifiers. Triage, evidence assembly and policy evaluation are connected. Missing models or snapshots route to review without invented scores.
- Drafts cite verified evidence. Optional AI can only arrange existing verified paragraphs; invalid or failed replies preserve the prior draft.
- Evaluation creates real persisted jobs. Model explanations measure model contributions; metric calculations handle tied scores. The split is exactly 1,050 training / 225 validation / 225 test cases, with all narrative examples held out.
- The operator website validates server responses, retains queue filters and pages, handles pending/failed/forbidden states, and follows the Column design tokens and typography. Fonts are self-hosted with their licenses.
- Operational, model, evaluation, data, demo and security documents now distinguish implemented behavior from planned and unverified behavior.

## Measured result

The checked-in [benchmark](../api/ml/reports/benchmark.json) is synthetic, seed 42, dataset synth-v1.5, model hgb-calibrated-v2, policy-v1.5. On 225 held-out cases, simulated net value is approximately INR 53,913 for rules-only, INR 46,058 for ML + policy, INR 13,994 for contest-everything and zero for contest-nothing. Rules-only wins this comparison. Test outcomes were not used to improve the model or pick its threshold.

The offline [seed manifest](../api/ml/reports/seed_manifest.json) records generated counts; it is not evidence that a hosted database has been seeded.

## Verification record

Final results are recorded here after the last local checks. Behavioral API tests use synthetic in-memory storage; PostgreSQL locking, deployed sign-in, hosted network behavior and an actual xAI request require separate verification. Formal browser automation remains deferred by AGENTS.md.

To check the product: sign in, open Disputes, search CB-DEMO-03 and confirm drafting is disabled while required proof is missing. Open CB-DEMO-01 and inspect its evidence citations. Change a queue filter, open a case and return to Queue to confirm the filter remains. Open Evaluation and compare all four measured strategies. Sign out and confirm console access requires sign-in again.

## Remaining release decisions

1. **Legacy cleanup — done.** The unused in-browser simulation files, unused UI packages, and the `_family` helper were removed after an explicit YES. Live labels remain in `types.ts`, `constants.ts`, and `format.ts`.
2. **Framework upgrade still requires YES.** Existing Python supporting libraries have published advisories; inspected affected features are not used. See [threat model](threat_model.md). This does not establish that the stack is free of security issues.
3. **Hosted release is unverified.** The checked-in Render build does not prepare the ignored model artifact. An approved build preparation step or durable artifact delivery is required. See [hosting](hosting.md). No shared reset is needed merely to restore an artifact. A matching model/data release, hosted sign-in and PostgreSQL concurrency checks are still required before claiming hosted readiness.
4. **Execution limits.** Evaluation can be interrupted when the server restarts; expired runs are marked failed on the next scheduling request. Sign-in has no MFA or dedicated brute-force limit. Benchmark results cannot establish real-world recovery or fraud detection quality.

## Technical detail (optional)

| Area | Source of truth / boundary |
| --- | --- |
| Website | TanStack Start, React 19, Tailwind v4; `src/routes`, `ops-api`, Zod response schemas, TanStack Query |
| API | FastAPI routes in `api/app/main.py`; services for cases, processing, drafting and evaluation |
| Storage | SQLAlchemy models and `api/alembic` revisions; PostgreSQL in production; no website product-table writes |
| Identity | Argon2 password hashes, hashed expiring bearer sessions, active role checks; sessionStorage token per locked stack |
| Decision flow | Snapshot → prediction → evidence → stored policy → role/state-checked action → audit |
| Model | Calibrated HistGradientBoosting, training-only explanation baseline, validation-only threshold, held-out report |
| Operations | Liveness/readiness/model endpoints, structured request logs, persisted evaluation jobs; Render/Vercel/Neon intended hosts |
| Local checks | pytest behavior/contract tests, Node schema/search tests, TypeScript, ESLint, Vite production build, browser inspection |

Automatic approval review rejected an earlier combined edit because removing a helper by truncating the server file could also remove routes. That command did not execute. The helper was later removed as a narrow edit after cleanup approval.
