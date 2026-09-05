import type {
  DisputeCategory,
  FeatureKey,
  ReasonFamily,
} from "./types";

export const CATEGORY_LABELS: Record<DisputeCategory, string> = {
  friendly_fraud_likely: "Friendly fraud likely",
  merchant_service_issue: "Merchant service issue",
  true_fraud_likely: "True fraud likely",
  technical_or_insufficient_information: "Insufficient information",
};

export const CATEGORY_SHORT: Record<DisputeCategory, string> = {
  friendly_fraud_likely: "Friendly fraud",
  merchant_service_issue: "Service issue",
  true_fraud_likely: "True fraud",
  technical_or_insufficient_information: "Insufficient info",
};

export const CATEGORY_HINT: Record<DisputeCategory, string> = {
  friendly_fraud_likely:
    "Signals suggest a legitimate purchase later disputed by the cardholder. Operational assessment only — not a legal finding.",
  merchant_service_issue:
    "Signals point to fulfillment, cancellation, refund, or product/service problems rather than unauthorized use.",
  true_fraud_likely:
    "Unauthorized or high-risk session/auth pattern. Default routing is human review under merchant policy.",
  technical_or_insufficient_information:
    "Records are incomplete or the dispute cannot be confidently categorized. Automation is blocked.",
};

export const REASON_FAMILY_LABELS: Record<ReasonFamily, string> = {
  unauthorized: "Unauthorized",
  not_received: "Not received",
  service_issue: "Service / quality",
  other: "Other",
};

export const FEATURE_LABELS: Record<FeatureKey, string> = {
  log_amount: "Log disputed amount",
  account_age_days: "Account tenure (days)",
  prior_successful_orders: "Prior successful orders",
  prior_disputes: "Prior disputes",
  prior_refunds: "Prior refunds",
  payment_method_age_days: "Payment method age",
  authentication_completed: "Authentication completed",
  three_ds_completed: "3DS completed",
  device_consistency: "Device consistency",
  location_consistency: "Location consistency",
  billing_descriptor_recognized: "Descriptor recognized",
  delivery_confirmed: "Delivery confirmed",
  shipped: "Shipment recorded",
  digital_access_proof: "Digital access proof",
  refund_requested: "Refund requested",
  cancellation_requested: "Cancellation requested",
  support_ticket_count: "Support tickets",
  customer_acknowledged: "Customer acknowledgment",
  hours_to_dispute: "Hours to dispute",
  session_to_purchase_min: "Session-to-purchase minutes",
  reason_unauthorized: "Reason: unauthorized",
  reason_not_received: "Reason: not received",
  reason_service_issue: "Reason: service",
  is_first_order: "First-time order",
  high_value_flag: "High-value flag",
  evidence_completeness: "Evidence completeness",
  segment_physical: "Physical goods merchant",
  segment_digital: "Digital merchant",
  prior_undisputed_ratio: "Prior undisputed ratio",
  login_proximity: "Login proximity to purchase",
};

export const STATE_LABELS: Record<string, string> = {
  received: "Received",
  normalized: "Normalized",
  triaged: "Triaged",
  evidence_collecting: "Collecting evidence",
  evidence_incomplete: "Evidence incomplete",
  policy_review: "Policy review",
  draft_ready: "Draft ready",
  human_review: "Human review",
  submitted_simulated: "Submitted (sim)",
  won_simulated: "Won (sim)",
  lost_simulated: "Lost (sim)",
  not_contested: "Not contested",
  closed: "Closed",
};

export const ACTION_LABELS: Record<string, string> = {
  prepare_representment_draft: "Prepare representment draft",
  request_human_review: "Route to human review",
  mark_evidence_incomplete: "Mark evidence incomplete",
  recommend_do_not_contest: "Do not contest",
  request_missing_evidence: "Request missing evidence",
  close_case: "Close case",
};
