import { Badge } from "@/components/ui/badge";
import {
  ACTION_LABELS,
  CATEGORY_SHORT,
  REASON_FAMILY_LABELS,
  STATE_LABELS,
} from "@/lib/chargebackos/constants";
import type {
  ActionType,
  CaseState,
  DisputeCategory,
  FightDecision,
  ReasonFamily,
} from "@/lib/chargebackos/types";

export function CategoryBadge({ value }: { value: DisputeCategory }) {
  const tone =
    value === "friendly_fraud_likely"
      ? "accent"
      : value === "true_fraud_likely"
        ? "danger"
        : value === "merchant_service_issue"
          ? "warn"
          : "neutral";
  return <Badge tone={tone}>{CATEGORY_SHORT[value]}</Badge>;
}

export function StateBadge({ value }: { value: CaseState }) {
  const tone =
    value === "draft_ready" || value === "won_simulated"
      ? "ok"
      : value === "human_review" || value === "evidence_incomplete"
        ? "warn"
        : value === "lost_simulated" || value === "not_contested"
          ? "neutral"
          : value === "closed"
            ? "neutral"
            : "info";
  return <Badge tone={tone}>{STATE_LABELS[value]}</Badge>;
}

export function FamilyBadge({ value }: { value: ReasonFamily }) {
  return <Badge tone="neutral">{REASON_FAMILY_LABELS[value]}</Badge>;
}

export function ActionBadge({ value }: { value: ActionType }) {
  const tone =
    value === "prepare_representment_draft"
      ? "ok"
      : value === "request_human_review" || value === "mark_evidence_incomplete"
        ? "warn"
        : "neutral";
  return <Badge tone={tone}>{ACTION_LABELS[value]}</Badge>;
}

export function FightBadge({ value }: { value: FightDecision }) {
  const label =
    value === "contest_recommended"
      ? "Contest"
      : value === "human_review_required"
        ? "Review"
        : "Do not contest";
  const tone =
    value === "contest_recommended"
      ? "ok"
      : value === "human_review_required"
        ? "warn"
        : "neutral";
  return <Badge tone={tone}>{label}</Badge>;
}

export function SplitBadge({ value }: { value: string }) {
  const tone = value === "test" ? "info" : "neutral";
  return <Badge tone={tone}>{value}</Badge>;
}
