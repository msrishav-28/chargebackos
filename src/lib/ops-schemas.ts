import { z } from "zod";
import { FEATURE_KEYS } from "./chargebackos/types.ts";

const text = z.string();
const count = z.number().int().nonnegative();
const number = z.number().finite();
const probability = number.min(0).max(1);
const category = z.enum(["friendly_fraud_likely", "merchant_service_issue", "true_fraud_likely", "technical_or_insufficient_information"]);
const family = z.enum(["unauthorized", "not_received", "service_issue", "other"]);
const profile = z.enum(["conservative", "balanced", "aggressive"]);
const segment = z.enum(["d2c_physical", "saas", "marketplace", "digital_goods"]);
export const actionSchema = z.enum(["prepare_representment_draft", "request_human_review", "mark_evidence_incomplete", "recommend_do_not_contest", "request_missing_evidence", "close_case"]);
export const stateSchema = z.enum(["received", "normalized", "triaged", "evidence_collecting", "evidence_incomplete", "policy_review", "draft_ready", "human_review", "submitted_simulated", "won_simulated", "lost_simulated", "not_contested", "closed"]);
const fight = z.enum(["contest_recommended", "human_review_required", "do_not_contest"]);
const strategy = z.enum(["contest_nothing", "contest_everything", "rules_only", "ml_policy"]);
const timestamp = z.iso.datetime({ offset: true });
const strings = z.array(text);
const signal = z.object({ feature: z.enum(FEATURE_KEYS), label: text, value: number, contribution: number, direction: z.enum(["supports", "opposes"]) });

export const staffSchema = z.object({ email: text, displayName: text, role: z.enum(["viewer", "analyst", "reviewer", "admin"]) });
export const loginSchema = z.object({ token: text.min(1), user: staffSchema });
export const successSchema = z.object({ ok: z.literal(true) });

const merchantSchema = z.object({ id: text, name: text, segment, policyProfile: profile });
const costSchema = z.object({ contestCostFixed: number, contestCostVariable: number, fpPenaltyFixed: number, fpPenaltyVariable: number, currency: z.literal("INR"), notes: text });
const classMetric = z.object({ precision: probability, recall: probability, f1: probability, support: count });
const threshold = z.object({ threshold: probability, precision: probability, recall: probability, expectedRecovery: number, falsePositiveCost: number, netValue: number, contested: count });
const strategyResult = z.object({ strategy, label: text, cases: count, contested: count, autoPrepared: count, humanReview: count, doNotContest: count, wins: count, losses: count, grossRecovery: number, contestCost: number, falsePositiveCost: number, netValue: number, coverageRate: probability, precisionContest: probability, recallWinnable: probability });
const evaluation = z.object({
  nTrain: count, nValid: count, nTest: count, frozen: z.literal(true), seed: count,
  datasetVersion: text, modelVersion: text, selectedThreshold: probability, thresholdRationale: text,
  classification: z.object({ accuracy: probability, macroF1: probability, perClass: z.record(category, classMetric), confusion: z.array(z.array(count).length(4)).length(4), labels: z.array(category).length(4) }),
  fightWorthiness: z.object({ prAuc: probability, rocAuc: probability, brier: probability, precision: probability, recall: probability, f1: probability, supportPositive: count }),
  calibration: z.object({ brierScore: probability, ece: probability, bins: z.array(z.object({ meanPred: probability, meanActual: probability, count, lower: probability, upper: probability })) }),
  thresholdCurve: z.array(threshold), strategies: z.array(strategyResult).length(4), operatingPoint: threshold,
  evidenceGaps: z.array(z.object({ key: text, label: text, missingCount: count })),
});
const failure = z.object({ caseId: text, trueCategory: category, predictedCategory: category, confidence: probability, topShap: z.array(signal), whyFailed: text, policyPreventedHarm: z.boolean(), policyAction: actionSchema });
const overview = z.object({ totalDisputes: count, totalDisputedAmount: number, potentialRecovery: number, simulatedRecovered: number, netValue: number, autoPrepRate: probability, humanReviewQueue: count, modelPrecision: probability, modelRecall: probability, modelMacroF1: probability, falsePositiveCost: number, coverageRate: probability, heldOutN: count });
export const overviewSchema = z.object({
  overview: overview.nullable(), evaluation: evaluation.nullable(), failureGallery: z.array(failure),
  costAssumptions: costSchema.nullable(), merchants: z.array(merchantSchema),
  queueCounts: z.object({ total: count, draftReady: count, humanReview: count, notContested: count }),
  modelVersion: text.nullable(), policyVersion: text, featureVersion: text, seed: count, datasetVersion: text.nullable(),
});

export const policiesSchema = z.object({
  policyVersion: text,
  profiles: z.array(z.object({ id: profile, label: text, description: text, minConfidence: probability, minWinProbability: probability, minExpectedValue: number, trueFraudDefault: z.enum(["human_review", "do_not_contest"]), maxAutoPrepRate: probability })),
  evidenceSchemas: z.array(z.object({ reasonFamily: family, required: strings, preferred: strings, optional: strings })),
});

const evidence = z.object({ reasonFamily: family, completenessScore: probability, mandatoryComplete: z.boolean(), missingRequired: strings, missingPreferred: strings, packageHash: text,
  items: z.array(z.object({ id: text, type: z.enum(["transaction", "delivery", "authentication", "communication", "customer_history"]), key: text, label: text, tier: z.enum(["required", "preferred", "optional"]), present: z.boolean(), sourceSystem: text, sourceReference: text, summary: text, value: text })),
});
const prediction = z.object({ modelVersion: text, featureVersion: text, predictedCategory: category, categoryConfidence: probability, classScores: z.record(category, probability), fightWorthinessProbability: probability, expectedRecoveredValue: number, shap: z.array(signal), calibrated: z.boolean() });
const policy = z.object({ policyVersion: text, profile, allowed: z.boolean(), recommendedAction: actionSchema, fightDecision: fight, blockReasons: strings, rulesEvaluated: z.array(z.object({ rule: text, passed: z.boolean(), detail: text })), inputSnapshotHash: text, evaluatedAt: timestamp });
const draft = z.object({ templateVersion: text, status: z.enum(["pending", "completed", "blocked", "failed"]), text, citations: z.array(z.object({ claim: text, evidenceId: text, evidenceLabel: text })), grounded: z.boolean() });
const snapshot = z.object({
  transaction: z.object({ amount: number, currency: z.literal("INR"), transactionAt: timestamp, paymentMethodAgeDays: count, authorizationApproved: z.boolean(), billingDescriptorRecognized: z.boolean() }),
  customerHistory: z.object({ accountAgeDays: count, priorSuccessfulOrders: count, priorDisputes: count, priorRefunds: count, priorUndisputedRatio: probability, regionBucket: text }),
  fulfillment: z.object({ type: z.enum(["physical", "digital", "service"]), orderConfirmedAt: timestamp, shipped: z.boolean(), delivered: z.boolean(), digitalAccess: z.boolean(), refundRequested: z.boolean(), cancellationRequested: z.boolean() }),
  sessionAuth: z.object({ authenticationCompleted: z.boolean(), threeDsCompleted: z.boolean(), deviceConsistency: probability, locationConsistency: probability, sessionToPurchaseMin: number, loginProximity: probability }),
  reasonContext: z.object({ reasonCode: text, reasonFamily: family, hoursToDispute: number }),
  merchantPolicyContext: z.object({ profile, segment }),
});

export const queueCaseSchema = z.object({
  id: text, externalDisputeId: text, merchantId: text, merchantName: text, merchantSegment: segment,
  policyProfile: profile, customerId: text, customerLabel: text, transactionId: text, orderId: text.nullable(),
  reasonCode: text, reasonFamily: family, reasonLabel: text, disputedAmount: number.nonnegative(), currency: z.literal("INR"),
  state: stateSchema, split: text, isDemo: z.boolean(), demoRole: text.nullable(), openedAt: timestamp, contestCost: number,
  prediction: prediction.nullable(), policyDecision: policy.nullable(), evidencePackage: evidence.nullable(),
});
export const disputeListSchema = z.object({ items: z.array(queueCaseSchema), total: count, page: count.min(1), limit: count.min(1).max(200) });
export const caseSchema = queueCaseSchema.extend({
  featureSnapshot: snapshot.nullable(), draft: draft.nullable(),
  trueCategory: category.nullable(), wouldWinIfContested: z.boolean().nullable(), latentWinProb: probability.nullable(),
  timeline: z.array(z.object({ id: text, at: timestamp, eventType: text, actor: text, actorRef: text.nullable(), beforeState: stateSchema.nullable(), afterState: stateSchema.nullable(), message: text })),
  simulatedOutcome: z.enum(["not_contested", "won_simulated", "lost_simulated"]).nullable(),
  recoveredAmount: number.nullable(), falsePositiveCost: number.nullable(), netValue: number.nullable(),
  allowedActions: z.array(actionSchema),
});
export const evaluationRunSchema = z.object({ batchRunId: text, state: z.enum(["queued", "running", "completed", "failed"]) });
export const evaluationStatusSchema = z.object({ id: text, state: z.enum(["queued", "running", "completed", "failed"]), summary: z.object({ error: text.optional() }) });
export type StaffUser = z.infer<typeof staffSchema>;
export type OverviewPayload = z.infer<typeof overviewSchema>;
export type ApiCase = z.infer<typeof caseSchema>;
