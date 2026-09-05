export type DisputeCategory =
  | "friendly_fraud_likely"
  | "merchant_service_issue"
  | "true_fraud_likely"
  | "technical_or_insufficient_information";

export type FightDecision =
  | "contest_recommended"
  | "human_review_required"
  | "do_not_contest";

export type CaseState =
  | "received"
  | "normalized"
  | "triaged"
  | "evidence_collecting"
  | "evidence_incomplete"
  | "policy_review"
  | "draft_ready"
  | "human_review"
  | "submitted_simulated"
  | "won_simulated"
  | "lost_simulated"
  | "not_contested"
  | "closed";

export type ReasonFamily =
  | "unauthorized"
  | "not_received"
  | "service_issue"
  | "other";

export type PolicyProfile = "conservative" | "balanced" | "aggressive";

export type MerchantSegment = "d2c_physical" | "saas" | "marketplace" | "digital_goods";

export type ActionType =
  | "prepare_representment_draft"
  | "request_human_review"
  | "mark_evidence_incomplete"
  | "recommend_do_not_contest"
  | "request_missing_evidence"
  | "close_case";

export type EvidenceType =
  | "transaction"
  | "delivery"
  | "authentication"
  | "communication"
  | "customer_history";

export type EvidenceTier = "required" | "preferred" | "optional";

export type Split = "train" | "validation" | "test";

export type StrategyId =
  | "contest_nothing"
  | "contest_everything"
  | "rules_only"
  | "ml_policy";

export type ActorType = "system" | "human" | "model" | "policy" | "simulation";

export type FulfillmentType = "physical" | "digital" | "service";

export const FEATURE_KEYS = [
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
] as const;

export type FeatureKey = (typeof FEATURE_KEYS)[number];

export interface Merchant {
  id: string;
  name: string;
  segment: MerchantSegment;
  policyProfile: PolicyProfile;
  timezone: string;
}

export interface FeatureSnapshot {
  transaction: {
    amount: number;
    currency: "INR";
    transactionAt: string;
    paymentMethodAgeDays: number;
    authorizationApproved: boolean;
    billingDescriptorRecognized: boolean;
  };
  customerHistory: {
    accountAgeDays: number;
    priorSuccessfulOrders: number;
    priorDisputes: number;
    priorRefunds: number;
    priorUndisputedRatio: number;
    regionBucket: string;
  };
  fulfillment: {
    type: FulfillmentType;
    orderConfirmedAt: string;
    shipped: boolean;
    delivered: boolean;
    digitalAccess: boolean;
    refundRequested: boolean;
    cancellationRequested: boolean;
  };
  sessionAuth: {
    authenticationCompleted: boolean;
    threeDsCompleted: boolean;
    deviceConsistency: number;
    locationConsistency: number;
    sessionToPurchaseMin: number;
    loginProximity: number;
  };
  reasonContext: {
    reasonCode: string;
    reasonFamily: ReasonFamily;
    hoursToDispute: number;
  };
  merchantPolicyContext: {
    profile: PolicyProfile;
    segment: MerchantSegment;
  };
}

export interface ShapItem {
  feature: FeatureKey;
  label: string;
  value: number;
  contribution: number;
  direction: "supports" | "opposes";
}

export interface ModelPrediction {
  modelVersion: string;
  featureVersion: string;
  predictedCategory: DisputeCategory;
  categoryConfidence: number;
  classScores: Record<DisputeCategory, number>;
  fightWorthinessProbability: number;
  expectedRecoveredValue: number;
  shap: ShapItem[];
  calibrated: boolean;
}

export interface EvidenceItem {
  id: string;
  type: EvidenceType;
  key: string;
  label: string;
  tier: EvidenceTier;
  present: boolean;
  sourceSystem: string;
  sourceReference: string;
  summary: string;
  value: string;
}

export interface EvidencePackage {
  reasonFamily: ReasonFamily;
  completenessScore: number;
  mandatoryComplete: boolean;
  missingRequired: string[];
  missingPreferred: string[];
  items: EvidenceItem[];
  packageHash: string;
}

export interface PolicyDecision {
  policyVersion: string;
  profile: PolicyProfile;
  allowed: boolean;
  recommendedAction: ActionType;
  fightDecision: FightDecision;
  blockReasons: string[];
  rulesEvaluated: { rule: string; passed: boolean; detail: string }[];
  inputSnapshotHash: string;
  evaluatedAt: string;
}

export interface RepresentmentDraft {
  templateVersion: string;
  status: "pending" | "completed" | "blocked" | "failed";
  text: string;
  citations: { claim: string; evidenceId: string; evidenceLabel: string }[];
  grounded: boolean;
}

export interface AuditEvent {
  id: string;
  at: string;
  eventType: string;
  actor: ActorType;
  actorRef?: string;
  beforeState?: CaseState;
  afterState?: CaseState;
  message: string;
}

export interface DisputeCase {
  id: string;
  externalDisputeId: string;
  merchantId: string;
  merchantName: string;
  merchantSegment: MerchantSegment;
  policyProfile: PolicyProfile;
  customerId: string;
  customerLabel: string;
  transactionId: string;
  orderId: string;
  reasonCode: string;
  reasonFamily: ReasonFamily;
  reasonLabel: string;
  disputedAmount: number;
  currency: "INR";
  openedAt: string;
  state: CaseState;
  split: Split;
  isDemo: boolean;
  demoRole?:
    | "friendly_fraud_autodraft"
    | "ambiguous_review"
    | "missing_evidence"
    | "true_fraud_review"
    | "negative_ev";
  features: Record<FeatureKey, number>;
  featureSnapshot: FeatureSnapshot;
  trueCategory: DisputeCategory;
  latentWinProb: number;
  wouldWinIfContested: boolean;
  prediction: ModelPrediction;
  evidencePackage: EvidencePackage;
  policyDecision: PolicyDecision;
  draft: RepresentmentDraft | null;
  timeline: AuditEvent[];
  simulatedOutcome: "won_simulated" | "lost_simulated" | "not_contested" | null;
  recoveredAmount: number;
  contestCost: number;
  falsePositiveCost: number;
  netValue: number;
}

export interface CostAssumptions {
  contestCostFixed: number;
  contestCostVariable: number;
  fpPenaltyFixed: number;
  fpPenaltyVariable: number;
  currency: "INR";
  notes: string;
}

export interface ClassMetric {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface ClassificationMetrics {
  accuracy: number;
  macroF1: number;
  perClass: Record<DisputeCategory, ClassMetric>;
  confusion: number[][];
  labels: DisputeCategory[];
}

export interface CalibrationBin {
  meanPred: number;
  meanActual: number;
  count: number;
  lower: number;
  upper: number;
}

export interface CalibrationReport {
  brierScore: number;
  ece: number;
  bins: CalibrationBin[];
}

export interface ThresholdPoint {
  threshold: number;
  precision: number;
  recall: number;
  expectedRecovery: number;
  falsePositiveCost: number;
  netValue: number;
  contested: number;
}

export interface StrategyResult {
  strategy: StrategyId;
  label: string;
  cases: number;
  contested: number;
  autoPrepared: number;
  humanReview: number;
  doNotContest: number;
  wins: number;
  losses: number;
  grossRecovery: number;
  contestCost: number;
  falsePositiveCost: number;
  netValue: number;
  coverageRate: number;
  precisionContest: number;
  recallWinnable: number;
}

export interface FailureCase {
  caseId: string;
  trueCategory: DisputeCategory;
  predictedCategory: DisputeCategory;
  confidence: number;
  topShap: ShapItem[];
  whyFailed: string;
  policyPreventedHarm: boolean;
  policyAction: ActionType;
}

export interface OverviewKpis {
  totalDisputes: number;
  totalDisputedAmount: number;
  potentialRecovery: number;
  simulatedRecovered: number;
  netValue: number;
  autoPrepRate: number;
  humanReviewQueue: number;
  modelPrecision: number;
  modelRecall: number;
  modelMacroF1: number;
  falsePositiveCost: number;
  coverageRate: number;
  heldOutN: number;
}

export interface EvaluationReport {
  nTrain: number;
  nValid: number;
  nTest: number;
  frozen: true;
  seed: number;
  datasetVersion: string;
  modelVersion: string;
  selectedThreshold: number;
  thresholdRationale: string;
  classification: ClassificationMetrics;
  fightWorthiness: {
    prAuc: number;
    rocAuc: number;
    brier: number;
    precision: number;
    recall: number;
    f1: number;
    supportPositive: number;
  };
  calibration: CalibrationReport;
  thresholdCurve: ThresholdPoint[];
  strategies: StrategyResult[];
  operatingPoint: ThresholdPoint;
  evidenceGaps: { key: string; label: string; missingCount: number }[];
}

export interface Universe {
  generatedAt: string;
  seed: number;
  datasetVersion: string;
  modelVersion: string;
  policyVersion: string;
  featureVersion: string;
  merchants: Merchant[];
  disputes: DisputeCase[];
  evaluation: EvaluationReport;
  failureGallery: FailureCase[];
  overview: OverviewKpis;
  costAssumptions: CostAssumptions;
}

export interface PolicyProfileConfig {
  id: PolicyProfile;
  label: string;
  description: string;
  minConfidence: number;
  minWinProbability: number;
  minExpectedValue: number;
  trueFraudDefault: "human_review" | "do_not_contest";
  maxAutoPrepRate: number;
}

export interface EvidenceSchema {
  reasonFamily: ReasonFamily;
  required: string[];
  preferred: string[];
  optional: string[];
}
