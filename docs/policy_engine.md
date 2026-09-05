# Policy Engine

The Policy Engine is the final deterministic authority in ChargebackOS. It is versioned, auditable, and completely independent from the ML/LLM layer. Its job is to block unsafe or uneconomical automated actions. Live implementation: `api/app/domain/policy.py`. Decisions persist in Neon as `policy_decisions`.

## Evaluation Order

For any automated representment action to occur, the case must pass the following gates in order:

1. **State Check:** Confirm the case is in a policy-evaluable state (`evidence_collecting` or `policy_review`).
2. **Action Validity:** The case service enforces the closed action vocabulary and lifecycle; reason family selects the evidence checklist.
3. **Evidence Completeness:** Check if all mandatory evidence required by the schema is present.
4. **Model Confidence:** Check if the ML triage classification meets the minimum confidence threshold.
5. **Expected Economic Value:** Ensure the expected recovered value exceeds the cost of contesting the dispute.
6. **Merchant Policy Profile:** Enforce specific merchant risk tolerance (e.g., conservative vs. aggressive routing).
7. **Human-Review Routing:** Check for sensitive categories (e.g., `true_fraud_likely` may always require human review depending on policy).
8. **Decision Output:** Produce an immutable policy decision record.

## Example Rules (Pseudo-code)

```python
def evaluate(case, prediction, evidence, merchant_policy):
    if case.state not in {"evidence_collecting", "policy_review"}:
        return block("invalid_case_state")
        
    if not evidence.mandatory_complete:
        return route_review("missing_required_evidence")
        
    if prediction.category_confidence < merchant_policy.min_confidence:
        return route_review("low_model_confidence")
        
    if prediction.fight_worthiness_probability < merchant_policy.min_win_probability:
        return recommend_drop("low_expected_win_probability")
        
    if prediction.expected_recovered_value < merchant_policy.min_expected_value:
        return recommend_drop("negative_expected_value")
        
    if prediction.predicted_category == "true_fraud_likely":
        return route_review("sensitive_risk_category")
        
    return allow("prepare_representment_draft")
```

## Policy Profiles

The system has fixed synthetic merchant profiles; thresholds are not editable in this submission:
- **Conservative:** High confidence threshold, routes heavily to human review, requires high expected value.
- **Balanced:** Moderate automation, normal expected-value threshold.
- **Aggressive:** Higher automation rates, but still never bypasses strict evidence requirements.

## Audit Contract

Every policy evaluation produces a `policy_decisions` record in the database containing:
- `policy_version`
- `allowed` (boolean)
- `recommended_action`
- `block_reasons_json`
- `input_snapshot_hash`

## Approval and enforcement

Policy `policy-v1.5` also checks calibrated-model status, conflicting evidence, insufficient-information categories and the projected merchant auto-preparation rate. Numeric profile thresholds are unchanged. The example is abbreviated; missing evidence and sensitive categories take priority over economics in the implementation.

A reviewer/admin can record a new passing human approval from human review, preserving the earlier blocked decision. Mandatory evidence is checked again against actual source records and cannot be waived. Analysts cannot approve from review.

Invalid transitions create distinct `action.blocked` audit events and return 409 while preserving the case and its action records. Retrying completed draft preparation does not duplicate an action. Optional AI arrangement requires an approved draft-ready case.
