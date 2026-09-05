from app.domain.constants import EVIDENCE_SCHEMAS, TEMPLATE_VERSION


def validate_draft_evidence(evidence: dict) -> None:
    schema = next((s for s in EVIDENCE_SCHEMAS if s["reasonFamily"] == evidence.get("reasonFamily")), None)
    if schema is None or not evidence.get("mandatoryComplete"):
        raise ValueError("Mandatory evidence is incomplete.")
    present = {
        item["key"] for item in evidence.get("items", [])
        if item.get("present") and str(item.get("summary", "")).strip()
        and item.get("sourceReference") not in (None, "", "—")
    }
    if not set(schema["required"]).issubset(present):
        raise ValueError("Mandatory evidence must have a source and a nonempty record.")


def _cite(evidence: dict, key: str) -> dict | None:
    for item in evidence["items"]:
        if item["key"] == key and item["present"]:
            return item
    return None


def build_grounded_draft(*, raw: dict, evidence: dict, policy: dict) -> dict:
    if not policy["allowed"]:
        return {
            "templateVersion": TEMPLATE_VERSION,
            "status": "blocked",
            "text": "Draft blocked by policy. No representment language is generated when the policy engine withholds approval.",
            "citations": [],
            "grounded": True,
        }

    validate_draft_evidence(evidence)

    citations: list[dict] = []
    lines: list[str] = []

    def push(claim: str, key: str | None) -> None:
        item = _cite(evidence, key) if key else None
        lines.append(f"{claim} [{item['id']}]" if item else claim)
        if key:
            if item:
                citations.append(
                    {"claim": claim, "evidenceId": item["id"], "evidenceLabel": item["label"]}
                )

    amount = raw["disputedAmount"]
    push(
        f"Representment draft for {raw['id']} · merchant {raw['merchant']['name']} · reason {raw['reasonCode']} ({raw['reasonLabel']}).",
        "transaction_record",
    )
    push(
        f"Disputed amount INR {amount:.2f} on transaction {raw['transactionId']}. Transaction time {raw['featureSnapshot']['transaction']['transactionAt']}.",
        "transaction_record",
    )
    family = raw["reasonFamily"]
    if family == "not_received":
        deliv = _cite(evidence, "delivery_confirmation")
        ship = _cite(evidence, "fulfillment_status")
        if deliv:
            push(
                f"Fulfillment record: {deliv['summary']}.",
                "delivery_confirmation",
            )
        elif ship:
            push(f"Fulfillment status on file: {ship['summary']}.", "fulfillment_status")
        ack = _cite(evidence, "customer_acknowledgment")
        if ack:
            push(f"Customer acknowledgment: {ack['summary']}.", "customer_acknowledgment")
    if family == "unauthorized":
        for key in ("authentication_indicator", "account_session_evidence", "three_ds_result", "prior_successful_link"):
            item = _cite(evidence, key)
            if item:
                push(f"{item['label']}: {item['summary']}.", key)
    if family == "service_issue":
        for key in ("support_history", "refund_timeline", "product_record"):
            item = _cite(evidence, key)
            if item:
                push(f"{item['label']}: {item['summary']}.", key)
    prior = _cite(evidence, "prior_undisputed_orders")
    if prior:
        push(f"Prior relationship: {prior['summary']}.", "prior_undisputed_orders")
    missing = evidence.get("missingPreferred") or []
    if missing:
        lines.append(f"Preferred evidence not on file (not asserted): {', '.join(missing)}.")
    lines.append(
        f"This draft uses only cited source records. It does not assert legal conclusions, does not claim the cardholder acted in bad faith, and is not a filing. Policy {policy['policyVersion']} allowed preparation under the {policy['profile']} profile."
    )
    return {
        "templateVersion": TEMPLATE_VERSION,
        "status": "completed",
        "text": "\n\n".join(lines),
        "citations": citations,
        "grounded": True,
    }
