from pathlib import Path

import yaml

DATASET_VERSION = "synth-v1.5"
MODEL_VERSION = "hgb-calibrated-v2"
POLICY_VERSION = "policy-v1.5"
FEATURE_VERSION = "features-v1"
TEMPLATE_VERSION = "representment-v2"
NOW_ISO = "2026-09-04T10:30:00.000Z"

COST_ASSUMPTIONS = {
    "contestCostFixed": 250.0,
    "contestCostVariable": 0.015,
    "fpPenaltyFixed": 900.0,
    "fpPenaltyVariable": 0.1,
    "currency": "INR",
}

CATEGORY_ORDER = [
    "friendly_fraud_likely",
    "merchant_service_issue",
    "true_fraud_likely",
    "technical_or_insufficient_information",
]

FEATURE_KEYS = [
    "log_amount",
    "account_age_days",
    "prior_successful_orders",
    "prior_disputes",
    "prior_refunds",
    "payment_method_age_days",
    "authentication_completed",
    "three_ds_completed",
    "device_consistency",
    "location_consistency",
    "billing_descriptor_recognized",
    "delivery_confirmed",
    "shipped",
    "digital_access_proof",
    "refund_requested",
    "cancellation_requested",
    "support_ticket_count",
    "customer_acknowledged",
    "hours_to_dispute",
    "session_to_purchase_min",
    "reason_unauthorized",
    "reason_not_received",
    "reason_service_issue",
    "is_first_order",
    "high_value_flag",
    "evidence_completeness",
    "segment_physical",
    "segment_digital",
    "prior_undisputed_ratio",
    "login_proximity",
]

FEATURE_LABELS = {
    "log_amount": "Log disputed amount",
    "account_age_days": "Account tenure (days)",
    "prior_successful_orders": "Prior successful orders",
    "prior_disputes": "Prior disputes",
    "prior_refunds": "Prior refunds",
    "payment_method_age_days": "Payment method age",
    "authentication_completed": "Authentication completed",
    "three_ds_completed": "3DS completed",
    "device_consistency": "Device consistency",
    "location_consistency": "Location consistency",
    "billing_descriptor_recognized": "Descriptor recognized",
    "delivery_confirmed": "Delivery confirmed",
    "shipped": "Shipment recorded",
    "digital_access_proof": "Digital access proof",
    "refund_requested": "Refund requested",
    "cancellation_requested": "Cancellation requested",
    "support_ticket_count": "Support tickets",
    "customer_acknowledged": "Customer acknowledgment",
    "hours_to_dispute": "Hours to dispute",
    "session_to_purchase_min": "Session-to-purchase minutes",
    "reason_unauthorized": "Reason: unauthorized",
    "reason_not_received": "Reason: not received",
    "reason_service_issue": "Reason: service",
    "is_first_order": "First-time order",
    "high_value_flag": "High-value flag",
    "evidence_completeness": "Evidence completeness",
    "segment_physical": "Physical goods merchant",
    "segment_digital": "Digital merchant",
    "prior_undisputed_ratio": "Prior undisputed ratio",
    "login_proximity": "Login proximity to purchase",
}

POLICY_PROFILES = {
    "conservative": {
        "id": "conservative",
        "label": "Conservative",
        "description": "High confidence bar, broad human review, never auto-prepares true-fraud or incomplete-evidence cases.",
        "minConfidence": 0.82,
        "minWinProbability": 0.55,
        "minExpectedValue": 200,
        "trueFraudDefault": "human_review",
        "maxAutoPrepRate": 0.22,
    },
    "balanced": {
        "id": "balanced",
        "label": "Balanced",
        "description": "Moderate automation with a 0.70 confidence gate and non-negative expected value.",
        "minConfidence": 0.7,
        "minWinProbability": 0.45,
        "minExpectedValue": 0,
        "trueFraudDefault": "human_review",
        "maxAutoPrepRate": 0.4,
    },
    "aggressive": {
        "id": "aggressive",
        "label": "Aggressive",
        "description": "Higher automation coverage. Mandatory evidence still cannot be bypassed.",
        "minConfidence": 0.58,
        "minWinProbability": 0.35,
        "minExpectedValue": -100,
        "trueFraudDefault": "human_review",
        "maxAutoPrepRate": 0.55,
    },
}

EVIDENCE_LABELS = {
    "transaction_record": "Transaction record",
    "order_confirmation": "Order confirmation",
    "fulfillment_status": "Fulfillment status",
    "delivery_confirmation": "Delivery confirmation",
    "carrier_scan": "Carrier scan",
    "communication_history": "Communication history",
    "prior_undisputed_orders": "Prior undisputed orders",
    "customer_acknowledgment": "Customer acknowledgment",
    "authentication_indicator": "Authentication indicator",
    "account_session_evidence": "Account / session evidence",
    "device_consistency": "Device consistency",
    "prior_successful_link": "Prior successful transaction",
    "three_ds_result": "3-D Secure result",
    "delivery_proof": "Delivery proof",
    "billing_descriptor": "Billing descriptor match",
    "support_history": "Support ticket history",
    "refund_timeline": "Refund request timeline",
    "cancellation_timeline": "Cancellation timeline",
    "product_record": "Product / service record",
}

REASON_CODES = {
    "unauthorized": [
        {"code": "4837", "label": "No cardholder authorization"},
        {"code": "10.4", "label": "Other fraud — card-absent"},
        {"code": "4850", "label": "Installment billing dispute"},
    ],
    "not_received": [
        {"code": "4855", "label": "Goods or services not received"},
        {"code": "13.1", "label": "Merchandise / services not received"},
    ],
    "service_issue": [
        {"code": "4853", "label": "Not as described / defective"},
        {"code": "13.3", "label": "Not as described"},
        {"code": "4860", "label": "Credit not processed"},
    ],
    "other": [
        {"code": "4513", "label": "Cancelled recurring"},
        {"code": "13.7", "label": "Cancelled merchandise / services"},
    ],
}

MERCHANT_SEED = [
    {"name": "Nimbus Home", "segment": "d2c_physical", "policy": "balanced"},
    {"name": "Kite Apparel", "segment": "d2c_physical", "policy": "aggressive"},
    {"name": "Saffron Box", "segment": "d2c_physical", "policy": "conservative"},
    {"name": "Peak Fitness", "segment": "d2c_physical", "policy": "balanced"},
    {"name": "Loom & Co", "segment": "d2c_physical", "policy": "balanced"},
    {"name": "Volt Gadgets", "segment": "d2c_physical", "policy": "aggressive"},
    {"name": "Mira Beauty", "segment": "d2c_physical", "policy": "conservative"},
    {"name": "Oak & Iron", "segment": "d2c_physical", "policy": "balanced"},
    {"name": "Gully Foods", "segment": "d2c_physical", "policy": "balanced"},
    {"name": "Dune Outdoor", "segment": "d2c_physical", "policy": "conservative"},
    {"name": "Arcadia Market", "segment": "marketplace", "policy": "conservative"},
    {"name": "SwiftCart", "segment": "marketplace", "policy": "balanced"},
    {"name": "Cedar Supply", "segment": "marketplace", "policy": "aggressive"},
    {"name": "Rivet Tools", "segment": "marketplace", "policy": "balanced"},
    {"name": "Harbor Ledger", "segment": "saas", "policy": "conservative"},
    {"name": "Cloudledger", "segment": "saas", "policy": "balanced"},
    {"name": "Stackpilot", "segment": "saas", "policy": "conservative"},
    {"name": "Pixel Classroom", "segment": "saas", "policy": "balanced"},
    {"name": "Northwind Digital", "segment": "digital_goods", "policy": "aggressive"},
    {"name": "Ember Studio", "segment": "digital_goods", "policy": "balanced"},
    {"name": "Quilt Media", "segment": "digital_goods", "policy": "conservative"},
    {"name": "Aura Wellness", "segment": "digital_goods", "policy": "balanced"},
    {"name": "Banyan Books", "segment": "digital_goods", "policy": "conservative"},
    {"name": "Petal Labs", "segment": "saas", "policy": "aggressive"},
    {"name": "Lotus Print", "segment": "d2c_physical", "policy": "balanced"},
]


def load_evidence_schemas() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "schemas" / "evidence" / "v1.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for family, spec in data["families"].items():
        out.append(
            {
                "reasonFamily": family,
                "required": spec["required"],
                "preferred": spec["preferred"],
                "optional": spec["optional"],
            }
        )
    return out


EVIDENCE_SCHEMAS = load_evidence_schemas()
