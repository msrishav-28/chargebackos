# ChargebackOS Demo Script

**Target Duration:** 5 Minutes
**Objective:** Prove that ChargebackOS is a defense-only, evidence-grounded risk-operations system that understands the financial trade-offs of dispute handling.

**Before you start (hosted):** open the Render `/health/live` URL and wait until it answers. Free Render sleeps after 15 minutes idle. Then open the Vercel website and sign in as analyst.

Website: TanStack Start on Vercel. API: FastAPI on Render. Data: Neon. Not Next.js.

## The Narrative Arc

### 1. The Problem (0:00 - 0:45)
- **Visual:** Show the ChargebackOS dashboard overview.
- **Talk Track:** "Merchant money is lost to disputes daily. Deciding which ones to contest is manual, error-prone, and often costs more in operational time than the recovered amount. ChargebackOS solves this by evaluating each dispute using only defensive data and a bounded decision path."

### 2. Ingestion & Triage (0:45 - 1:45)
- **Visual:** Open a new, incoming dispute in the Queue.
- **Action:** Click into a case that looks like friendly fraud (e.g., customer has a history of undisputed orders, delivery is confirmed).
- **Talk Track:** "The server scores the stored feature snapshot. We can inspect its classification, calibrated probability and approximate Shapley contributions. These explain model behavior relative to a training reference; they are not a finding about the cardholder."

### 3. The Policy Engine (1:45 - 2:30)
- **Visual:** Scroll to the Evidence & Policy section.
- **Talk Track:** "AI alone is dangerous. We gate every decision with a deterministic Policy Engine. Read the stored decision on this case — the narrative label does not force approval. If the gates pass, Confirm auto-draft is enabled. Route to review, Do not contest, and Close stay disabled on a draft-ready case because those moves are not allowed from that stage."

### 4. Bounded Response (2:30 - 3:15)
- **Visual:** Show the generated representment draft.
- **Talk Track:** "The server prepares cited evidence paragraphs. Optional AI can arrange them, but cannot add or change facts. This is a draft for staff review; nothing is filed."

### 5. Safety & Human Review (3:15 - 4:00)
- **Visual:** Navigate back to the queue and open a different case—one with missing evidence or low confidence.
- **Talk Track:** "What happens when things are uncertain? Here's an ambiguous case. The Policy Engine blocks automated action because it fails the confidence threshold. It immediately routes the case to a human reviewer. We prioritize safety over blind automation."

### 6. Batch Proof & Evaluation (4:00 - 5:00)
- **Visual:** Switch to the Evaluation & Metrics page.
- **Talk Track:** "This page compares the frozen test results with three baselines and includes false-positive costs. The current rules-only baseline earns more simulated net value than ML + policy. We report that limitation instead of hiding it. The submission demonstrates controlled actions, evidence checks and honest measurement, not a proven production economic win."

## Concrete checks before presenting

1. Open CB-DEMO-01 and read its actual stored policy result. Its narrative label does not force approval; a reviewer may approve only with complete mandatory evidence. Do not click disabled buttons to “show errors.”
2. Open CB-DEMO-03 and verify the missing-evidence list and blocked drafting. Confirm auto-draft is disabled. Routing to review, if enabled, must not make missing evidence acceptable.
3. Sign in as viewer; action controls must be disabled. Sign-out must work on desktop and mobile.
4. Use Next in Disputes, open a case, then return. The filters and page should remain.
5. An admin can run evaluation and see a new run identifier and completion/failure status. Do not reset during a pitch: reset replaces shared case history.

Optional AI is not required for a local demonstration. No live filing, refunds, customer contact or payment attempts occur.
