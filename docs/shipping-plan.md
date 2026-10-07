# ChargebackOS: PayPal submission delivery plan

Decision date: 7 October 2026. Status: recovery changes prepared; live deployment unverified; PayPal integration not implemented. This is the execution plan, not a claim of completed functionality.

## Product decision

**ChargebackOS is an evidence-first dispute workbench for small PayPal merchants.** An operator imports a sandbox dispute, sees the evidence and economic case for responding, reviews a grounded response, and exports an auditable packet. Its strongest demonstration is both a justified response and a justified refusal to draft when required evidence is missing.

Primary user: a merchant operations analyst handling a small daily dispute queue. Job: decide what needs attention, understand what is missing, and prepare a defensible response without searching across several records. We optimize preparation quality and operator time. We do not claim actual recovered revenue, fraud detection accuracy on real customers, or guaranteed dispute wins.

The differentiation is visible restraint: source-linked evidence, explicit unknowns, policy gates, reviewer accountability, and honest evaluation. A chatbot alone is not the product.

## Submission constraints

Official rules reviewed on 7 October: PayPal sandbox integration plus AI; existing projects require significant in-period updates; a working build, public open-source repository, English materials, and a public YouTube demo under three minutes. Judging weights implementation, design, impact, innovation, and presentation equally. Submission closes **12 November 2026, 12:00 PST / 13 November 2026, 01:30 IST**. Keep judging access available through 15 December. Internal submission target: **10 November, 18:00 IST**.

Source: https://paypalaihackathon.devpost.com/rules . Recheck before submission. Record the existing repository baseline (`00e56f5`) and the work completed during the hackathon in the submission. Select and obtain owner acceptance of an open-source license before publishing the final release; no license was present in the inspected root.

## Architecture and scope decisions

| Area | Decision | Reason / acceptance |
| --- | --- | --- |
| Web | Keep TanStack Start, React, existing Vercel deployment shape | Current build passes; avoid a framework migration |
| API | Keep FastAPI on Render | One authority for permissions, policies, evidence and case transitions |
| Database | Supabase PostgreSQL for every existing application table | No Neon connection remains in the deployed system after cutover |
| Authentication | Keep FastAPI password/session flow; move users and sessions with all other tables | Migrating the database does not require replacing identity protocols |
| Supabase exposure | Backend SQL only; deny browser roles on product/operator tables | Password hashes, session hashes, labels and audit records stay inaccessible to public API keys |
| PayPal | One sandbox seller account, server-side credentials, Disputes API ingestion | Genuine provider data must power the primary workflow |
| AI | Existing measured tabular model for synthetic evaluation; source-constrained language drafting | Do not apply synthetic model confidence to provider cases as a validated probability |
| Evidence | Structured source records and cited packet export | Every draft fact is traceable; missing facts remain missing |
| Execution | Existing Postgres job rows; bounded API requests | Avoid introducing Redis, Celery, or a microservice split for the submission |
| Money and filing | No live funds, refunds, customer contact, or live chargeback filing | Sandbox case review and export are sufficient product scope |

No checkout-store detour, new payment recovery product, multi-provider platform, subscription billing, or multi-agent marketing feature. A single merchant workbench must be excellent before scope grows.

## What the audit established

- Source baseline: 52 API tests passed locally, including the API/web schema contract; web typecheck, lint, build and three schema tests passed. Tests mostly use a SQLite behavior adapter, so they do not establish hosted PostgreSQL behavior.
- The Render build was running migrations and seed writes. Building a candidate release could therefore mutate the current database before deployment succeeded.
- Alembic placed the database URL through ConfigParser interpolation, which can reject percent-encoded passwords.
- TLS normalization was Neon-specific. There was no bounded PostgreSQL connection timeout or Supabase browser-role protection in the original migration.
- Hosting documentation disagreed with the actual Blueprint about hooks, build seeding and artifact generation.
- Existing login rejects an unconfigured `AUTH_SECRET`; seeding rejects a weak/default `DEMO_PASSWORD`. An unset production `VITE_API_URL` also prevents the frontend from reaching the API. These are investigation points, not confirmed causes of the current outage.
- The source still referenced Razorpay; there was no PayPal adapter. Amount formatting and seeded records assume INR. PayPal currency support needs explicit work.
- The initial Alembic revision imports current ORM metadata. Freeze its schema before adding new PayPal tables, or fresh-install upgrades can accidentally create future tables before their revisions run.

## Delivery sequence

Dates are targets in IST. Each milestone has an exit gate; a failed gate gets fixed before downstream release.

| Target | Deliverable | Exit gate |
| --- | --- | --- |
| Oct 7–9 | Recover hosting and migrate to Supabase | All health endpoints, hosted login, queue and representative case work after a redeploy; data reconciliation signed off |
| Oct 10–14 | Real PayPal sandbox vertical slice | Authorized seller lists and imports one real sandbox dispute; transaction, amount, currency and provider status match PayPal; re-import is idempotent |
| Oct 15–20 | Evidence review and grounded AI response | Source-linked packet, missing-evidence block, review-required state, editable draft with audit history and export work end to end |
| Oct 21–25 | Complete operator experience | Queue → case → evidence → decision → response → export; errors, empty states, keyboard navigation and narrow screens verified |
| Oct 26–30 | Reliability and adversarial cases | Retry/replay, authorization, stale status, amount/currency, missing model, provider outage and evidence injection tests pass |
| Oct 31–Nov 4 | Measured demo and pitch | Five reproducible cases, observed timings, known limitations, screenshots, install guide and first video cut |
| Nov 5–8 | Release candidate | Clean setup from README, judge account, production browser test and restore drill; feature freeze |
| Nov 9–10 | Submission | Public licensed repository, final video and Devpost entry verified; receipt retained |
| Nov 11–12 | Contingency buffer | Fix submission/access defects only; no new product features |
| Through Dec 15 | Judging availability | Stable release and access instructions remain usable |

## Recovery and full database migration

The detailed operator procedure is in [hosting.md](hosting.md). First identify the actual frontend URL, Render service and deployed commit, Supabase target project, and whether existing Neon records must be retained. Preserve records by default.

1. Capture the current failing request, HTTP status, Render build/start error and health responses. Check frontend API origin, CORS, secrets presence and Alembic version without exposing secrets.
2. Back up the source database and inventory all application tables, counts, primary keys, foreign keys and current revision. Preserve operator roles and password hashes. Keep the authentication secret stable to retain valid session hashes, or deliberately revoke sessions as a separate documented action.
3. Use a dedicated Supabase target. Copy the exact Session pooler URI from its Connect panel, using port 5432 and TLS. Do not reconstruct its hostname from a region string. Configure the migration URL with a direct or session connection; transaction pooling is not the migration path.
4. Rehearse restore into the empty target. Transfer only ChargebackOS application schema/data, not source provider roles or Supabase-managed schemas. Apply the new security revision after restoring the previous schema. Verify access as the backend owner and denial for browser roles.
5. Briefly pause source writes for final transfer, reconcile counts and critical records, switch both runtime and migration URLs, then redeploy Render. Do not seed over a restored book.
6. For a confirmed fresh demo target, run Alembic then the existing non-reset seed command once. Measure seed duration; it performs many database round trips and is not part of every web-server start.
7. Verify database, model, all four operator roles, queue, demo cases, allowed and blocked actions, audit events and refresh persistence from the hosted browser. Restart/redeploy once and repeat the critical path.
8. Keep the source backup until target acceptance. Do not delete Neon, reset shared data or resume writes to two competing databases. Decommissioning is a separate explicit operation after acceptance.

Completion evidence: deployed SHA, target project identifier, migration revision, reconciled counts, redacted health results, browser flow recording and absence of Neon hosts in active application settings. Code compatibility alone is not a completed migration.

## PayPal implementation backlog

### Provider connection and import

- Prove sandbox seller permissions and create a repeatable buyer/seller dispute fixture during the first integration milestone. Test account availability immediately; do not leave it until video day.
- Add a backend-only adapter with an allowlisted sandbox base URL, OAuth token cache, bounded timeouts and redacted error handling. Persist PayPal debug IDs for diagnosis without storing credentials in audit messages.
- Implement authenticated sync and single-dispute import. Follow pagination; handle rate limits and expired tokens. Do not blindly retry writes. No arbitrary caller-supplied provider URLs.
- Add provider records keyed by provider + seller + external dispute ID, with provider status, reason, deadlines, timestamps, raw payload provenance and source checksum. Keep provider status separate from local review state.
- Store monetary values as Decimal with explicit currency. Remove the assumption that every queue amount is INR; do not sum different currencies or use one hardcoded handling cost across them. Unsupported currencies go to review with an explanation.
- Import actual transaction and dispute fields. Missing fulfillment/authentication evidence must not be filled from the synthetic generator. Unknown reason codes and incomplete records enter review.
- Keep a clearly labeled synthetic scenario mode for deterministic tests. A fixture replay is never presented as a live PayPal API call. The release still requires the real sandbox path to work.

### Evidence and AI

- Treat provider text and uploaded evidence as untrusted data. Bound size and type; store provenance and a content hash. Never execute instructions inside evidence.
- Construct one normalized evidence bundle. Required fields come from explicit reason mappings; source timestamps and gaps stay visible.
- For sandbox cases, present policy-based readiness and evidence completeness. Synthetic win estimates stay on the evaluation screen until there is suitable validation data.
- Language drafting receives only the authorized structured bundle. Each factual claim must map to an evidence ID. Reject unsupported citations or facts; save provider/model version and generation outcome.
- On language-provider timeout, show the available grounded template and label it as a template; do not claim AI success. No draft action can override a stored policy block.
- An analyst prepares a response; a reviewer approves a version tied to the evidence hash. Evidence changes invalidate approval. Export a human-readable packet plus structured JSON with citations, policy outcome and audit history.

## Product design specification

Retain the existing Column visual language in `DESIGN.md`. Emphasis belongs on decisions and evidence, with restrained status colors and legible monetary data.

| Screen | Primary job | Required content and behavior |
| --- | --- | --- |
| Login | Get the judge/operator into a working demo | Clear setup failure, wrong-password and waking states; no frontend secret values |
| Overview | Know what needs attention | Cases by local state, deadlines, evidence gaps; source/sandbox labels; no fabricated recovered-revenue KPI |
| Disputes | Select the next case | Search, status, reason, currency, source, amount and deadline; stable pagination and preserved filters |
| Case workspace | Understand one recommended action | Header with source IDs; evidence panel; policy reasons; response panel; timeline; explicit reviewer action |
| Evidence panel | Verify every assertion | Present/missing status, provenance, timestamps, source references, unsupported-data explanations |
| Response review | Approve a grounded version | Inline citations, missing-evidence block, version/hash, edit history and export |
| Evaluation | Inspect model limitations | Frozen synthetic benchmark, four baselines, false-positive cost, failure gallery and honest rules-versus-ML comparison |
| About / demo guide | Understand scope quickly | Sandbox boundary, system diagram, walkthrough and known limitations |

One primary action per case state. Disabled actions explain why. Loading never becomes a blank screen; failure never becomes fake data. Keyboard focus remains visible, statuses have text labels, and the core case view works at 390px and 1440px widths.

## Verification and release gates

- **Build:** typecheck, lint, production build, API/web contract and all API behavior tests pass in CI.
- **Database:** actual PostgreSQL migrations succeed with encoded passwords; foreign keys/JSONB behave correctly; browser roles cannot access application tables; import counts reconcile.
- **Authorization:** unauthenticated reads fail; viewer mutations fail; analyst cannot perform reviewer/admin actions. The public judge account is never an admin account.
- **Integrity:** duplicate provider events/imports create no duplicate cases; stale evidence cannot approve an old draft; illegal transitions record blocked actions without changing the case.
- **Resilience:** database outage, missing model, LLM timeout, PayPal rate limit and malformed provider payload produce bounded failures with a recoverable interface.
- **Browser:** hosted login → imported PayPal case → evidence → policy → review/export, plus missing-evidence block and page refresh, pass on the release candidate.
- **Honesty:** synthetic metrics are labeled; no claim of real-world win rate, savings or model superiority without supporting measurement. Provider success is verified in PayPal, not inferred from a green UI toast.
- **Operations:** health checks, environment settings and deployed revision documented; no reset/seed endpoint exposed to a public privileged account; secrets absent from source, browser bundles and logs.

## Demo and submission package

Target video length: 2:40. Opening 20 seconds: merchant problem and product promise. Next 30 seconds: sync a genuine sandbox dispute and show its source identity. Next 55 seconds: inspect evidence, explain the decision, review and export the cited response. Next 30 seconds: demonstrate an evidence gap blocking preparation. Final 25 seconds: audit trail, measured synthetic evaluation, limitations and why the workflow matters.

Prepare: hosted URL, least-privilege judge credentials through submission instructions, public repository and license, reproducible setup, screenshots, short architecture description, limitations, dated change log from the pre-hackathon baseline, and a public YouTube link. Record actual operator task timings across the five cases; do not invent ROI.

## Ownership and current access boundary

I handle architecture, implementation, tests, product decisions, reviewable pull requests, deployment instructions and submission drafting within this workspace. The project owner supplies account access/configuration, confirms licensing and existing-data retention, records/publishes the final video, and submits the entry.

Render and Supabase connections were declined for this session. Live logs, target inventory, database transfer and host configuration cannot currently be verified here. Next inputs: deployed web/API URLs, redacted Render failure logs, and confirmation of whether the Supabase project already exists and Neon data must be preserved. Never paste database passwords or API secrets into GitHub issues or this plan.
