# Threat Model & Defense-Only Posture

ChargebackOS is an **AI Risk Manager** submission limited to synthetic merchant-defense workflows. This document describes controls and limits; it is not a security certification.

## 1. Defense-Only Guarantees

- **No Fraud Simulation or Card Testing:** The system does not generate synthetic identities for testing external systems, nor does it contain logic to probe payment gateways.
- **Defense-Only Ingestion:** The service stores dispute events against verified references; it does not move money, issue refunds, or contact customers.
- **Bounded Interventions:** The action vocabulary is strictly closed (`prepare_representment_draft`, `request_human_review`, `close_case`). The system cannot invent new operational actions.

## 2. LLM Prompt Injection & Hallucination Defenses

- **Evidence Isolation:** The LLM does not perform open-ended web searches. It is provided a rigid JSON schema containing only the validated `evidence_items` attached to the case.
- **Citation Enforcement:** Server-generated paragraphs cite source IDs. Optional AI returns only their order. Missing, duplicated or invented indexes and free-form prose are rejected. Provider failures preserve the existing draft and produce an audit event.
- **Policy Supremacy:** Even if the LLM hallucinates a recommendation to auto-submit a draft, the deterministic Policy Engine evaluates the case *before* any action is taken. The LLM has zero execution authority.

## 3. Data Leakage (ML Pipeline)

To ensure the model evaluates true risk rather than "cheating" with future knowledge:
- **Frozen Features:** The generator freezes decision-time features separately from outcomes. New ingests reuse a stored transaction snapshot with provenance. This is not a historical production feature store.
- **Forbidden Features:** The model is explicitly prevented from seeing post-dispute artifacts, such as future support replies, analyst decision labels, or final chargeback arbitration results.

## 4. State Machine Integrity

- Transitions between case states (e.g., from `triaged` to `draft_ready`) are strictly enforced by the backend API.
- Invalid state transition requests (e.g., attempting to generate a draft for a case missing mandatory evidence) are intercepted by the Policy Engine, logged to the `audit_events` table as an `action.blocked` event, and return an HTTP 409 Conflict.

## 5. Synthetic Data Privacy

Product records are synthetic. Staff emails, password hashes, session tokens and hosting credentials still require protection. Never commit or log credential values.

## 6. Hosting and sign-in

- FastAPI on Render, website on Vercel, data on Neon. Render free sleeps; the UI must not fake a healthy book while the API is down.
- Sign-in is email/password in Neon. Not bank-grade identity. Sessions fail closed on every API route.
- The product does not email, SMS, or retry cards. That would be a different (dunning) product.

See [hosting.md](hosting.md).

## Reviewed limits (2026-09-05)

- Inactive or unknown-role staff cannot sign in or reuse a session. Viewers cannot write. Only reviewer/admin can approve from review, and neither can waive mandatory evidence.
- Tokens in sessionStorage are accessible to scripts on the website. This pass has no MFA or dedicated brute-force protection. It is not bank-grade identity.
- The npm production audit reported zero advisories. Official PyPI records list advisories for installed Starlette 0.46.2 and python-multipart 0.0.20. Inspection found no upload/form parsing, file-serving endpoints, HTTPEndpoint subclasses, TrustedHost middleware or hostname-based authorization using the affected paths. This is an applicability review, not a penetration test.
- Framework upgrades require owner approval. Sources: [Starlette advisories](https://pypi.org/pypi/starlette/0.46.2/json), [python-multipart advisories](https://pypi.org/pypi/python-multipart/0.0.20/json).
- PostgreSQL locking and hosted configuration remain unverified by the local in-memory tests.
