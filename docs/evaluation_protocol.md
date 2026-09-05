# Evaluation Protocol

ChargebackOS measures whether ML adds value under explicit synthetic cost assumptions. Batch results are stored by FastAPI in Neon (`batch_runs`, `evaluation_metrics`), not invented in the browser.

## 1. Train / Validation / Test Split

The synthetic dataset uses stratified random allocation with fixed seed 42:
- **70% Training:** Used for fitting the gradient boosting model.
- **15% Validation:** Used for threshold selection and probability calibration. Model hyperparameters are fixed in code.
- **15% Held-Out Test:** Used for model and strategy metrics. Queue counts and evidence-gap summaries describe the wider book.

## 2. False-Positive Cost Model

A naive model might choose to contest every dispute, resulting in high gross recovery but massive operational costs and potential merchant penalty fees. We evaluate using an honest expected-value formulation:

`expected_value = p_win × disputed_amount - contest_cost - expected_false_positive_penalty`

Definitions:
- **True Positive:** Contesting a defensible case (Net = Recovered Amount - Handling Cost).
- **False Positive:** Contesting an indefensible case (Net = - Handling Cost - Penalty/Goodwill Loss).
- **False Negative:** Dropping a winnable case (Net = 0, but lost opportunity).
- **True Negative:** Correctly dropping a bad case (Net = 0).

## 3. Baselines for Comparison

Every batch evaluation compares the ML-assisted strategy against three baselines:
1. **Contest Nothing:** Zero handling cost, zero recovery.
2. **Contest Everything:** Maximum coverage, but massive false-positive costs.
3. **Rules-Only Triage:** A deterministic system relying solely on dispute amount and crude evidence presence.
4. **ChargebackOS (ML + Policy):** The full system.

## 4. Required Reporting Metrics

The evaluation outputs must include:
- Total Disputed Amount vs. Simulated Recovered Amount.
- Precision, Recall, and Macro F1 on the held-out set.
- Calibration Quality (Brier Score or Reliability Diagram).
- Count of cases sent to: Auto-Preparation, Human Review, and Do Not Contest.
- Total Net Value (incorporating false-positive costs).

## 5. The Honest Failure Gallery

ChargebackOS maintains a documented gallery of 5–10 misclassified cases from the test set. For each, we document:
- The predicted vs. true class.
- The model's confidence and top SHAP features.
- The disagreement and measured model signals; these do not establish a causal explanation of failure.
- Whether the deterministic Policy Engine successfully intercepted the bad prediction (preventing a harmful automated action).

## Exact operating point and interpretation

The default allocation is 1,050 training, 225 validation and 225 test records. Narrative cases are reserved on test before allocating ordinary records. This is neither a time holdout nor a merchant holdout.

Threshold selection searches 0.10–0.80 in 0.02 increments on validation, maximizing net value among candidates with at least 75% contest precision and complete mandatory evidence. If none qualifies, the diagnostic fallback is disclosed. The chart includes the exact chosen threshold. ROC-AUC groups tied scores correctly; PR-AUC is trapezoidal area, not average precision.

Merchant policy thresholds are separate fixed controls. ML + policy includes a reviewer simulation requiring complete evidence, positive expected value and p(win) at least 0.50. Review routing and simulated do-not-contest counts can overlap. This does not measure real reviewer performance.

An admin can start a real run from Evaluation. Queued/running/completed/failed status is persisted; repeated requests with one Idempotency-Key reuse the run. Runs recompute the matching frozen synthetic benchmark and do not change case actions.

The [current measured report](../api/ml/reports/benchmark.json) favors rules-only on net value. This limitation must remain in presentations.
