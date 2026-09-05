# Model Card: ChargebackOS Triage & Fight-Worthiness Model

## Model Details
- **Architecture this pass:** scikit-learn `HistGradientBoostingClassifier` with isotonic calibration on the validation split. Same model family as XGBoost/LightGBM. Those packages remain later; we do not pretend the file is XGBoost.
- **Task:** 
  1. Dispute Category Classification (4-class).
  2. Fight-Worthiness Scoring (Expected Win Probability).
- **Version:** `hgb-calibrated-v2`
- **Framework:** scikit-learn. Artifact: `api/ml/artifacts/model.joblib`.

## Intended Use
- **Primary Use Case:** Triaging incoming merchant chargebacks to estimate defensibility and routing cases for automated evidence assembly or human review.
- **Out-of-Scope Uses:** 
  - Real-time transaction fraud blocking (this model operates *post-dispute*).
  - Consumer credit scoring.
  - Making final automated decisions without deterministic policy gates.

## Data & Features
- **Training Data this pass:** seeded synthetic disputes (~1,500 cases, 25 merchants). The master spec’s extra 15,000 undisputed ledger rows are later, not the default seed.
- **Feature Groups:**
  - **Transaction Features:** Log amount, authentication completion, payment-method age and descriptor recognition.
  - **Customer History:** Account age, prior successful orders, prior disputes.
  - **Fulfillment:** Order confirmation, delivery status.
  - **Session Proxies:** Device consistency bucket, authentication completion indicator.
- **Data Leakage Controls:** Strictly excludes post-dispute outcomes (e.g., final chargeback result, future refunds) and limits features to data available at the time the dispute was filed.

## Evaluation
- **Split:** 70% Train / 15% Validation (used for threshold tuning and probability calibration) / 15% Held-Out Test.
- **Metrics:** Precision per class, Recall per class, Macro F1, PR-AUC (for contest-worthiness), Brier Score (for calibration quality).
- **Calibration:** Isotonic regression on validation with frozen fitted classifiers. Probabilities are not adjusted by hand afterward. Synthetic calibration does not establish real-world calibration.

## Limitations & Bias
- **Synthetic Bias:** The model is trained on a synthetic dataset; real-world payment data has different distributions, seasonality, and adversarial drift.
- **Explainability Constraint:** Four fixed forward/reverse permutation pairs estimate Shapley contributions against the training-median feature vector. All 30 contributions sum to the predicted-class probability difference from that reference. The UI shows the largest eight. Correlated features and a single reference limit interpretation; these values do not establish causation.

## Safety & Posture
- This model is strictly **defense-only**. It cannot generate offensive fraud tactics, evasion flows, or exploit instructions.

## Reproduction and measured result

From `api/`, run `python -m app.train` without a database. It writes the ignored model artifact and `ml/reports/benchmark.json`. `python -m app.train --evaluate-only` reuses the matching artifact.

Dataset `synth-v1.5` fixes the old split allocator: the default split is exactly 1,050 / 225 / 225, with all five narrative cases on test. Model v2 replaces unrelated feature bars and removes post-calibration probability adjustments. These local version changes did not overwrite hosted records.

The [measured benchmark](../api/ml/reports/benchmark.json) currently gives **lower simulated net value to ML + policy than to rules-only**. Do not present a proven improvement over rules. Model settings and thresholds were not tuned to improve the observed test result.
