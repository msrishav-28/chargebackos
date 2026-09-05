from __future__ import annotations

import math
import hashlib
import json
from datetime import datetime, timedelta, timezone
from sklearn.model_selection import train_test_split

from app.domain.constants import (
    CATEGORY_ORDER,
    COST_ASSUMPTIONS,
    EVIDENCE_LABELS,
    EVIDENCE_SCHEMAS,
    FEATURE_KEYS,
    MERCHANT_SEED,
    REASON_CODES,
)
from app.domain.prng import chance, clamp, hash8, mulberry32, pick, rand_int, randn


def fulfillment_for(segment: str) -> str:
    if segment in ("d2c_physical", "marketplace"):
        return "physical"
    if segment == "saas":
        return "service"
    return "digital"


def evidence_type_for(key: str) -> str:
    if key in ("transaction_record", "billing_descriptor", "product_record"):
        return "transaction"
    if key in (
        "order_confirmation",
        "fulfillment_status",
        "delivery_confirmation",
        "carrier_scan",
        "delivery_proof",
        "digital_access_proof",
    ):
        return "delivery"
    if key in ("authentication_indicator", "account_session_evidence", "device_consistency", "three_ds_result"):
        return "authentication"
    if key in (
        "communication_history",
        "customer_acknowledgment",
        "support_history",
        "refund_timeline",
        "cancellation_timeline",
    ):
        return "communication"
    return "customer_history"


def source_for(kind: str) -> str:
    return {
        "transaction": "ledger.synthetic",
        "delivery": "fulfillment.synthetic",
        "authentication": "auth.synthetic",
        "communication": "support.synthetic",
    }.get(kind, "crm.synthetic")


def schema_for(family: str) -> dict:
    return next(s for s in EVIDENCE_SCHEMAS if s["reasonFamily"] == family)


def evidence_completeness(family: str, available: set[str]) -> float:
    schema = schema_for(family)
    return clamp(sum(weight * sum(key in available for key in schema[tier]) / max(1, len(schema[tier]))
                     for tier, weight in (("required", 0.6), ("preferred", 0.3), ("optional", 0.1))), 0, 1)


def build_evidence(family: str, presence: dict[str, bool], values: dict[str, str], case_id: str) -> dict:
    schema = schema_for(family)
    items = []

    def push(key: str, tier: str) -> None:
        present = bool(presence.get(key)) and bool(values.get(key, "").strip())
        kind = evidence_type_for(key)
        items.append(
            {
                "id": f"ev-{case_id}-{key}",
                "type": kind,
                "key": key,
                "label": EVIDENCE_LABELS.get(key, key),
                "tier": tier,
                "present": present,
                "sourceSystem": source_for(kind),
                "sourceReference": f"src_{hash8(case_id + key)}" if present else "—",
                "summary": values.get(key, "Record present in source system.") if present else "Not available at decision time.",
                "value": values.get(key, "present") if present else "",
            }
        )

    for k in schema["required"]:
        push(k, "required")
    for k in schema["preferred"]:
        push(k, "preferred")
    for k in schema["optional"]:
        push(k, "optional")
    available = {item["key"] for item in items if item["present"]}
    missing_required = [k for k in schema["required"] if k not in available]
    missing_preferred = [k for k in schema["preferred"] if k not in available]
    completeness = evidence_completeness(family, available)
    payload = json.dumps(items, sort_keys=True, separators=(",", ":"))
    return {
        "reasonFamily": family,
        "completenessScore": completeness,
        "mandatoryComplete": len(missing_required) == 0,
        "missingRequired": [EVIDENCE_LABELS.get(k, k) for k in missing_required],
        "missingPreferred": [EVIDENCE_LABELS.get(k, k) for k in missing_preferred],
        "items": items,
        "packageHash": hashlib.sha256(payload.encode()).hexdigest()[:16],
    }


def merchants_from_seed() -> list[dict]:
    return [
        {
            "id": f"m_{str(i + 1).zfill(2)}",
            "name": m["name"],
            "segment": m["segment"],
            "policyProfile": m["policy"],
            "timezone": "Asia/Kolkata",
        }
        for i, m in enumerate(MERCHANT_SEED)
    ]


def softmax4(a: float, b: float, c: float, d: float) -> tuple[float, float, float, float]:
    m = max(a, b, c, d)
    ea, eb, ec, ed = math.exp(a - m), math.exp(b - m), math.exp(c - m), math.exp(d - m)
    s = ea + eb + ec + ed
    return ea / s, eb / s, ec / s, ed / s


def contest_cost(amount: float) -> float:
    return COST_ASSUMPTIONS["contestCostFixed"] + COST_ASSUMPTIONS["contestCostVariable"] * amount


def sample_latent(rng, segment: str, force: dict | None = None) -> dict:
    force = force or {}
    first_order = force.get("firstOrder", chance(rng, 0.22))
    account_age = force.get("accountAgeDays", rand_int(rng, 1, 28) if first_order else rand_int(rng, 40, 1400))
    prior_orders = force.get("priorOrders", 0 if first_order else rand_int(rng, 1, 48))
    prior_disputes = force.get("priorDisputes", rand_int(rng, 1, 3) if chance(rng, 0.12) else 0)
    prior_refunds = force.get("priorRefunds", rand_int(rng, 1, 4) if chance(rng, 0.18) else 0)
    if segment == "saas":
        amount_base = math.exp(6.4 + 0.55 * randn(rng))
    elif segment == "digital_goods":
        amount_base = math.exp(6.1 + 0.7 * randn(rng))
    else:
        amount_base = math.exp(7.2 + 0.75 * randn(rng))
    amount = force.get("amount", clamp(round(amount_base), 199, 89999))
    high_value = force.get("highValue", amount >= 12000)
    if "family" in force:
        family = force["family"]
    else:
        family = pick(
            rng,
            ("unauthorized", "service_issue", "other", "unauthorized")
            if segment in ("digital_goods", "saas")
            else ("not_received", "service_issue", "unauthorized", "not_received"),
        )
    auth = force.get("auth", chance(rng, 0.42 if first_order else 0.78))
    three_ds = force.get("threeDs", auth and chance(rng, 0.62))
    device = force.get("device", clamp(0.55 + 0.4 * rng() if auth else 0.15 + 0.35 * rng(), 0, 1))
    location = force.get("location", clamp(0.5 + 0.45 * rng() if auth else 0.12 + 0.4 * rng(), 0, 1))
    descriptor = force.get("descriptor", chance(rng, 0.74))
    fulfill = fulfillment_for(segment)
    shipped = force.get("shipped", chance(rng, 0.82) if fulfill == "physical" else chance(rng, 0.08))
    delivered = force.get(
        "delivered",
        chance(rng, 0.78) if shipped else (fulfill != "physical" and chance(rng, 0.7)),
    )
    digital_access = force.get("digitalAccess", fulfill != "physical" and chance(rng, 0.72))
    refund_req = force.get("refundReq", chance(rng, 0.16))
    cancel_req = force.get("cancelReq", chance(rng, 0.45 if refund_req else 0.08))
    tickets = force.get(
        "tickets",
        rand_int(rng, 1, 4) if refund_req or cancel_req else (rand_int(rng, 1, 2) if chance(rng, 0.12) else 0),
    )
    ack = force.get("ack", chance(rng, 0.4 if delivered else 0.12))
    hours = force.get("hoursToDispute", clamp(round(math.exp(3.4 + 1.1 * randn(rng))), 4, 720))
    session_min = force.get("sessionMin", clamp(round(math.exp(1.6 + 0.9 * randn(rng))), 1, 240))
    pay_age = force.get("payAge", rand_int(rng, 0, 18) if first_order else rand_int(rng, 20, 900))
    login_prox = force.get("loginProx", clamp(0.55 + 0.4 * rng() if auth else 0.1 + 0.3 * rng(), 0, 1))
    prior_undisputed = 0 if prior_orders <= 0 else clamp((prior_orders - prior_disputes) / prior_orders, 0, 1)
    completeness = 0.55 + 0.2 * rng()
    knobs = {
        "amount": amount,
        "accountAgeDays": account_age,
        "priorOrders": prior_orders,
        "priorDisputes": prior_disputes,
        "priorRefunds": prior_refunds,
        "payAge": pay_age,
        "auth": auth,
        "threeDs": three_ds,
        "device": device,
        "location": location,
        "descriptor": descriptor,
        "delivered": delivered,
        "shipped": shipped,
        "digitalAccess": digital_access,
        "refundReq": refund_req,
        "cancelReq": cancel_req,
        "tickets": tickets,
        "ack": ack,
        "hoursToDispute": hours,
        "sessionMin": session_min,
        "family": family,
        "firstOrder": first_order,
        "highValue": high_value,
        "segment": segment,
        "loginProx": login_prox,
        "completeness": completeness,
        "priorUndisputedRatio": prior_undisputed,
    }
    ff = (
        -0.15
        + 1.7 * (1 if delivered else 0)
        + 1.4 * (1 if auth else 0)
        + 1.1 * prior_undisputed
        + 0.7 * clamp(account_age / 365, 0, 3)
        + 0.5 * (1 if descriptor else 0)
        - 1.4 * (1 if refund_req else 0)
        - 1.0 * (1 if first_order else 0)
        - 0.8 * (1 if family == "unauthorized" else 0)
        + 1.15 * randn(rng)
    )
    svc = (
        0.05
        + 1.9 * (1 if refund_req else 0)
        + 1.5 * clamp(tickets / 3, 0, 2)
        + 1.3 * (1 if cancel_req else 0)
        + 1.1 * (1 if family == "service_issue" else 0)
        - 0.7 * (1 if delivered else 0)
        + 1.15 * randn(rng)
    )
    fraud = (
        0.15
        + 2.0 * (1 if family == "unauthorized" else 0)
        + 1.8 * (0 if auth else 1)
        + 1.5 * (1 - location)
        + 1.2 * (1 if first_order else 0)
        + 0.9 * (1 if high_value else 0)
        - 1.1 * clamp(account_age / 365, 0, 3)
        - 0.9 * clamp(prior_orders / 10, 0, 3)
        + 1.15 * randn(rng)
    )
    tech = -0.2 + 1.8 * (1 - completeness) + 1.1 * (1 if (not auth and not delivered) else 0) + 1.0 * randn(rng)
    probs = softmax4(ff, svc, fraud, tech)
    if force.get("trueCategory"):
        true_cat = force["trueCategory"]
    else:
        u = rng()
        acc = 0.0
        true_cat = CATEGORY_ORDER[0]
        for i, lab in enumerate(CATEGORY_ORDER):
            acc += probs[i]
            if u <= acc:
                true_cat = lab
                break
    if true_cat == "friendly_fraud_likely":
        knobs["delivered"] = force.get("delivered", chance(rng, 0.88) if fulfill == "physical" else knobs["delivered"])
        knobs["auth"] = force.get("auth", chance(rng, 0.9))
        knobs["ack"] = force.get("ack", chance(rng, 0.55))
    elif true_cat == "merchant_service_issue":
        knobs["refundReq"] = force.get("refundReq", chance(rng, 0.72))
        knobs["tickets"] = force.get("tickets", rand_int(rng, 1, 5))
        knobs["cancelReq"] = force.get("cancelReq", chance(rng, 0.4))
    elif true_cat == "true_fraud_likely":
        knobs["auth"] = force.get("auth", chance(rng, 0.22))
        knobs["threeDs"] = force.get("threeDs", False)
        knobs["location"] = force.get("location", clamp(0.08 + 0.28 * rng(), 0, 1))
        knobs["device"] = force.get("device", clamp(0.1 + 0.3 * rng(), 0, 1))
        knobs["firstOrder"] = force.get("firstOrder", chance(rng, 0.7))
    knobs["trueCategory"] = true_cat
    return knobs


def evidence_presence(rng, family: str, knobs: dict, true_cat: str, force_missing=False, force_complete=False):
    schema = schema_for(family)
    presence: dict[str, bool] = {}
    values: dict[str, str] = {}
    p_required = 0.55 if true_cat == "technical_or_insufficient_information" else 0.78 if true_cat == "true_fraud_likely" else 0.94
    p_preferred = 0.78 if true_cat == "friendly_fraud_likely" else 0.7 if true_cat == "merchant_service_issue" else 0.48
    p_optional = 0.4 + 0.25 * rng()

    def maybe(key: str, p: float, value: str) -> None:
        present = chance(rng, p)
        presence[key] = present
        if present:
            values[key] = value

    tx_value = f"INR {knobs['amount']:,.0f} · auth {'approved' if knobs['auth'] else 'partial'}"
    maybe("transaction_record", 1 if force_missing else p_required, tx_value)
    maybe("order_confirmation", 0.35 if force_missing else p_required, f"Confirmed {rand_int(rng, 1, 18)}h after payment")
    maybe(
        "fulfillment_status",
        p_required if knobs["shipped"] or knobs["digitalAccess"] else 0.35,
        "Delivered" if knobs["delivered"] else "In transit" if knobs["shipped"] else "Access granted" if knobs["digitalAccess"] else "Unfulfilled",
    )
    maybe("delivery_confirmation", p_preferred if knobs["delivered"] else 0.08, "Carrier delivered · signature/OTP captured" if knobs["delivered"] else "")
    maybe("carrier_scan", p_preferred if knobs["shipped"] else 0.1, "Origin + destination scans present" if knobs["shipped"] else "")
    maybe("communication_history", 0.85 if knobs["tickets"] > 0 else p_optional, f"{knobs['tickets']} support tickets on file" if knobs["tickets"] > 0 else "No outbound dispute comms")
    maybe("prior_undisputed_orders", 0.8 if knobs["priorOrders"] > 2 else 0.2, f"{max(0, knobs['priorOrders'] - knobs['priorDisputes'])} prior undisputed orders")
    maybe("customer_acknowledgment", 0.9 if knobs["ack"] else 0.12, "Customer confirmed receipt in-app" if knobs["ack"] else "")
    maybe("authentication_indicator", 0.92 if knobs["auth"] else 0.4, "Issuer auth approved" if knobs["auth"] else "Auth not completed")
    maybe("account_session_evidence", p_required, f"Device {knobs['device']:.2f} · location {knobs['location']:.2f}")
    maybe("device_consistency", p_preferred if knobs["device"] > 0.6 else 0.25, f"Score {knobs['device']:.2f}")
    maybe("prior_successful_link", p_preferred if knobs["priorOrders"] > 0 else 0.15, "Same instrument used on undisputed order" if knobs["priorOrders"] > 0 else "")
    maybe("three_ds_result", 0.9 if knobs["threeDs"] else 0.2, "3DS friction completed" if knobs["threeDs"] else "3DS not performed")
    maybe("delivery_proof", p_optional if knobs["delivered"] else 0.08, "Proof-of-delivery document" if knobs["delivered"] else "")
    maybe("billing_descriptor", 0.85 if knobs["descriptor"] else 0.2, "Descriptor recognized on statement" if knobs["descriptor"] else "Descriptor mismatch risk")
    maybe("support_history", 0.9 if knobs["tickets"] > 0 else 0.4 if family == "service_issue" else 0.2, f"{knobs['tickets']} tickets" if knobs["tickets"] > 0 else "No tickets")
    maybe("refund_timeline", 0.88 if knobs["refundReq"] else 0.1, "Refund requested before chargeback" if knobs["refundReq"] else "No refund request")
    maybe("cancellation_timeline", 0.85 if knobs["cancelReq"] else 0.1, "Cancellation requested" if knobs["cancelReq"] else "No cancellation")
    maybe("product_record", p_preferred, "Catalog SKU + terms snapshot")
    if force_complete:
        for key in schema["required"]:
            presence[key] = True
            values.setdefault(key, "Record present at decision time.")
    if force_missing:
        req = [k for k in schema["required"] if k != "transaction_record"] or schema["required"]
        drop = pick(rng, req)
        presence[drop] = False
        values.pop(drop, None)
    if true_cat == "technical_or_insufficient_information":
        drop = pick(rng, schema["required"])
        presence[drop] = False
        values.pop(drop, None)
    return presence, values


def features_from(knobs: dict, completeness: float) -> dict:
    prior_undisputed = 0 if knobs["priorOrders"] <= 0 else clamp((knobs["priorOrders"] - knobs["priorDisputes"]) / knobs["priorOrders"], 0, 1)
    return {
        "log_amount": math.log(max(1, knobs["amount"])),
        "account_age_days": knobs["accountAgeDays"],
        "prior_successful_orders": knobs["priorOrders"],
        "prior_disputes": knobs["priorDisputes"],
        "prior_refunds": knobs["priorRefunds"],
        "payment_method_age_days": knobs["payAge"],
        "authentication_completed": 1 if knobs["auth"] else 0,
        "three_ds_completed": 1 if knobs["threeDs"] else 0,
        "device_consistency": knobs["device"],
        "location_consistency": knobs["location"],
        "billing_descriptor_recognized": 1 if knobs["descriptor"] else 0,
        "delivery_confirmed": 1 if knobs["delivered"] else 0,
        "shipped": 1 if knobs["shipped"] else 0,
        "digital_access_proof": 1 if knobs["digitalAccess"] else 0,
        "refund_requested": 1 if knobs["refundReq"] else 0,
        "cancellation_requested": 1 if knobs["cancelReq"] else 0,
        "support_ticket_count": knobs["tickets"],
        "customer_acknowledged": 1 if knobs["ack"] else 0,
        "hours_to_dispute": knobs["hoursToDispute"],
        "session_to_purchase_min": knobs["sessionMin"],
        "reason_unauthorized": 1 if knobs["family"] == "unauthorized" else 0,
        "reason_not_received": 1 if knobs["family"] == "not_received" else 0,
        "reason_service_issue": 1 if knobs["family"] == "service_issue" else 0,
        "is_first_order": 1 if knobs["firstOrder"] else 0,
        "high_value_flag": 1 if knobs["highValue"] else 0,
        "evidence_completeness": completeness,
        "segment_physical": 1 if knobs["segment"] in ("d2c_physical", "marketplace") else 0,
        "segment_digital": 1 if knobs["segment"] in ("digital_goods", "saas") else 0,
        "prior_undisputed_ratio": prior_undisputed,
        "login_proximity": knobs["loginProx"],
    }


def snapshot_from(knobs: dict, merchant: dict, tx_at: str, reason_code: str) -> dict:
    fulfill = fulfillment_for(merchant["segment"])
    prior_undisputed = 0 if knobs["priorOrders"] <= 0 else clamp((knobs["priorOrders"] - knobs["priorDisputes"]) / knobs["priorOrders"], 0, 1)
    return {
        "transaction": {
            "amount": knobs["amount"],
            "currency": "INR",
            "transactionAt": tx_at,
            "paymentMethodAgeDays": knobs["payAge"],
            "authorizationApproved": knobs["auth"],
            "billingDescriptorRecognized": knobs["descriptor"],
        },
        "customerHistory": {
            "accountAgeDays": knobs["accountAgeDays"],
            "priorSuccessfulOrders": knobs["priorOrders"],
            "priorDisputes": knobs["priorDisputes"],
            "priorRefunds": knobs["priorRefunds"],
            "priorUndisputedRatio": prior_undisputed,
            "regionBucket": pick(mulberry32(knobs["accountAgeDays"] + 9), ["IN-West", "IN-South", "IN-North", "IN-East", "IN-Metro"]),
        },
        "fulfillment": {
            "type": fulfill,
            "orderConfirmedAt": tx_at,
            "shipped": knobs["shipped"],
            "delivered": knobs["delivered"],
            "digitalAccess": knobs["digitalAccess"],
            "refundRequested": knobs["refundReq"],
            "cancellationRequested": knobs["cancelReq"],
        },
        "sessionAuth": {
            "authenticationCompleted": knobs["auth"],
            "threeDsCompleted": knobs["threeDs"],
            "deviceConsistency": knobs["device"],
            "locationConsistency": knobs["location"],
            "sessionToPurchaseMin": knobs["sessionMin"],
            "loginProximity": knobs["loginProx"],
        },
        "reasonContext": {"reasonCode": reason_code, "reasonFamily": knobs["family"], "hoursToDispute": knobs["hoursToDispute"]},
        "merchantPolicyContext": {"profile": merchant["policyProfile"], "segment": merchant["segment"]},
    }


def win_prob(knobs: dict, cat: str, completeness: float) -> float:
    z = (
        -1.15
        + (1.35 if cat == "friendly_fraud_likely" else 0)
        + (-0.15 if cat == "merchant_service_issue" else 0)
        + (-1.85 if cat == "true_fraud_likely" else 0)
        + (-1.35 if cat == "technical_or_insufficient_information" else 0)
        + 1.15 * completeness
        + 0.55 * (1 if knobs["delivered"] else 0)
        + 0.4 * (1 if knobs["auth"] else 0)
        + 0.25 * (1 if knobs["ack"] else 0)
        - 0.45 * (1 if knobs["refundReq"] else 0)
        - 0.2 * math.log(max(1, knobs["amount"])) / 8
    )
    if z > 12:
        p = 1.0
    elif z < -12:
        p = 0.0
    else:
        p = 1 / (1 + math.exp(-z))
    return clamp(p, 0.04, 0.92)


def make_case(rng, merchants: list[dict], seq: int, opts: dict | None = None) -> dict:
    opts = opts or {}
    merchant = opts.get("merchant") or pick(rng, merchants)
    knobs = sample_latent(rng, merchant["segment"], opts.get("force"))
    reason = pick(rng, REASON_CODES[knobs["family"]])
    presence, values = evidence_presence(
        rng,
        knobs["family"],
        knobs,
        knobs["trueCategory"],
        opts.get("forceMissingRequired", False),
        opts.get("forceCompleteRequired", False),
    )
    case_id = opts.get("id") or f"CB-{str(1000 + seq).zfill(4)}"
    pkg = build_evidence(knobs["family"], presence, values, case_id)
    knobs["completeness"] = pkg["completenessScore"]
    feats = features_from(knobs, pkg["completenessScore"])
    hours = knobs["hoursToDispute"]
    opened = datetime.fromisoformat("2026-08-28T12:00:00+00:00") - timedelta(hours=rand_int(rng, 2, 360))
    tx_at = (opened - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")
    p_win = win_prob(knobs, knobs["trueCategory"], pkg["completenessScore"])
    if opts.get("isDemo"):
        would_win = knobs["trueCategory"] == "friendly_fraud_likely" or chance(rng, p_win)
    else:
        would_win = chance(rng, p_win) and not chance(rng, 0.12)
    tenure = knobs["accountAgeDays"]
    if knobs["firstOrder"]:
        customer_label = f"new · {tenure}d tenure"
    elif knobs["priorOrders"] > 12:
        customer_label = f"loyal · {tenure}d tenure"
    else:
        customer_label = f"returning · {tenure}d tenure"
    return {
        "seq": seq,
        "id": case_id,
        "externalDisputeId": f"dp_{hash8(case_id)}",
        "merchant": merchant,
        "customerId": f"c_{hash8('cust' + case_id)}",
        "customerLabel": customer_label,
        "transactionId": f"txn_{hash8('tx' + case_id)}",
        "orderId": f"ord_{hash8('or' + case_id)}",
        "reasonCode": reason["code"],
        "reasonFamily": knobs["family"],
        "reasonLabel": reason["label"],
        "disputedAmount": knobs["amount"],
        "openedAt": opened.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "isDemo": bool(opts.get("isDemo")),
        "demoRole": opts.get("demoRole"),
        "features": feats,
        "featureSnapshot": snapshot_from(knobs, merchant, tx_at, reason["code"]),
        "evidenceItems": pkg["items"],
        "evidencePackage": pkg,
        "trueCategory": knobs["trueCategory"],
        "latentWinProb": p_win,
        "wouldWinIfContested": would_win,
        "contestCost": contest_cost(knobs["amount"]),
        "split": opts.get("split", "train"),
    }


def assign_splits(seed: int, cases: list[dict]) -> None:
    ordinary = [case for case in cases if not case["isDemo"]]
    for case in cases:
        case["split"] = "test"
    if not ordinary:
        return
    n_train, n_valid = math.floor(len(cases) * 0.7), math.floor(len(cases) * 0.15)
    train, remaining = train_test_split(ordinary, train_size=n_train, random_state=seed,
                                       stratify=[c["trueCategory"] for c in ordinary])
    valid, _ = train_test_split(remaining, train_size=n_valid, random_state=seed + 1,
                                stratify=[c["trueCategory"] for c in remaining])
    for case in train:
        case["split"] = "train"
    for case in valid:
        case["split"] = "validation"


def generate_world(seed: int = 42, target: int = 1500) -> dict:
    rng = mulberry32(seed)
    merchants = merchants_from_seed()
    cases: list[dict] = []
    by_name = {m["name"]: m for m in merchants}

    def demo(seq: int, **kwargs) -> None:
        cases.append(make_case(rng, merchants, seq, kwargs))

    demo(1, id="CB-DEMO-01", isDemo=True, demoRole="friendly_fraud_autodraft", merchant=by_name["Nimbus Home"], split="test", forceCompleteRequired=True, force={"trueCategory": "friendly_fraud_likely", "family": "not_received", "amount": 4899, "accountAgeDays": 612, "priorOrders": 11, "priorDisputes": 0, "priorRefunds": 0, "firstOrder": False, "auth": True, "threeDs": True, "device": 0.91, "location": 0.88, "descriptor": True, "delivered": True, "shipped": True, "ack": True, "refundReq": False, "cancelReq": False, "tickets": 0, "highValue": False, "hoursToDispute": 216})
    demo(2, id="CB-DEMO-02", isDemo=True, demoRole="ambiguous_review", merchant=by_name["Harbor Ledger"], split="test", force={"trueCategory": "merchant_service_issue", "family": "service_issue", "amount": 12900, "accountAgeDays": 44, "priorOrders": 1, "firstOrder": False, "auth": True, "threeDs": False, "device": 0.52, "location": 0.49, "delivered": False, "shipped": False, "digitalAccess": True, "refundReq": True, "tickets": 2, "cancelReq": False, "highValue": True})
    demo(3, id="CB-DEMO-03", isDemo=True, demoRole="missing_evidence", merchant=by_name["Arcadia Market"], split="test", forceMissingRequired=True, force={"trueCategory": "technical_or_insufficient_information", "family": "not_received", "amount": 3299, "accountAgeDays": 90, "priorOrders": 2, "delivered": False, "shipped": True, "auth": True})
    demo(4, id="CB-DEMO-04", isDemo=True, demoRole="true_fraud_review", merchant=by_name["Northwind Digital"], split="test", forceCompleteRequired=True, force={"trueCategory": "true_fraud_likely", "family": "unauthorized", "amount": 18999, "accountAgeDays": 6, "priorOrders": 0, "firstOrder": True, "auth": False, "threeDs": False, "device": 0.18, "location": 0.11, "descriptor": False, "delivered": False, "digitalAccess": False, "highValue": True, "hoursToDispute": 14})
    demo(5, id="CB-DEMO-05", isDemo=True, demoRole="negative_ev", merchant=by_name["Saffron Box"], split="test", force={"trueCategory": "merchant_service_issue", "family": "service_issue", "amount": 249, "accountAgeDays": 210, "priorOrders": 3, "priorRefunds": 2, "refundReq": True, "tickets": 3, "delivered": False, "auth": True, "highValue": False})
    for i in range(len(cases), target):
        cases.append(make_case(rng, merchants, i + 1))
    assign_splits(seed + 99, cases)
    return {"merchants": merchants, "cases": cases, "seed": seed}
