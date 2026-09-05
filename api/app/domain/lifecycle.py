from app.domain.constants import NOW_ISO
from uuid import uuid4

ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "received": ["normalized"],
    "normalized": ["triaged", "human_review"],
    "triaged": ["evidence_collecting"],
    "evidence_collecting": ["evidence_incomplete", "policy_review"],
    "evidence_incomplete": ["human_review"],
    "policy_review": ["draft_ready", "human_review", "not_contested"],
    "draft_ready": ["submitted_simulated"],
    "submitted_simulated": ["won_simulated", "lost_simulated"],
    "human_review": ["draft_ready", "not_contested", "triaged"],
    "won_simulated": ["closed"],
    "lost_simulated": ["closed"],
    "not_contested": ["closed"],
    "closed": [],
}

OPERATOR_EXCEPTIONS = {
    ("human_review", "draft_ready"),
    ("human_review", "not_contested"),
    ("evidence_incomplete", "human_review"),
    ("not_contested", "closed"),
}


def can_transition(frm: str, to: str) -> bool:
    return to in ALLOWED_TRANSITIONS.get(frm, []) or (frm, to) in OPERATOR_EXCEPTIONS


def operator_actions(
    state: str,
    role: str,
    *,
    policy_allowed: bool,
    mandatory_complete: bool,
) -> list[str]:
    """Staff actions the current case will accept. Hiding a button is not security."""
    if role not in {"analyst", "reviewer", "admin"}:
        return []
    allowed: list[str] = []
    can_prepare = can_transition(state, "draft_ready") or state == "draft_ready"
    if can_prepare and mandatory_complete:
        if state == "human_review":
            if role in {"reviewer", "admin"}:
                allowed.append("prepare_representment_draft")
        elif policy_allowed:
            allowed.append("prepare_representment_draft")
    if can_transition(state, "human_review") and state != "human_review":
        allowed.append("request_human_review")
    if can_transition(state, "not_contested"):
        allowed.append("recommend_do_not_contest")
    if role in {"reviewer", "admin"} and can_transition(state, "closed"):
        allowed.append("close_case")
    return allowed


def state_from_policy(action: str, mandatory_complete: bool) -> str:
    if not mandatory_complete:
        return "evidence_incomplete"
    return {
        "prepare_representment_draft": "draft_ready",
        "request_human_review": "human_review",
        "mark_evidence_incomplete": "evidence_incomplete",
        "recommend_do_not_contest": "not_contested",
        "request_missing_evidence": "evidence_incomplete",
        "close_case": "closed",
    }[action]


def target_state(action: str) -> str:
    targets = {
        "request_human_review": "human_review",
        "recommend_do_not_contest": "not_contested",
        "prepare_representment_draft": "draft_ready",
        "close_case": "closed",
        "mark_evidence_incomplete": "evidence_incomplete",
        "request_missing_evidence": "evidence_incomplete",
    }
    if action not in targets:
        raise ValueError("Unknown case action.")
    return targets[action]


def make_audit(
    case_id: str,
    event_type: str,
    message: str,
    *,
    actor: str = "system",
    actor_ref: str | None = None,
    before: str | None = None,
    after: str | None = None,
    at: str | None = None,
) -> dict:
    return {
        "id": f"ae-{case_id}-{uuid4().hex}",
        "at": at or NOW_ISO,
        "eventType": event_type,
        "actor": actor,
        "actorRef": actor_ref,
        "beforeState": before,
        "afterState": after,
        "message": message,
    }
