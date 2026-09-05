from __future__ import annotations

import math

from sklearn.metrics import auc, precision_recall_curve, roc_auc_score

from app.domain.constants import CATEGORY_ORDER, COST_ASSUMPTIONS, DATASET_VERSION


def _fp(amount: float) -> float:
    return COST_ASSUMPTIONS["fpPenaltyFixed"] + COST_ASSUMPTIONS["fpPenaltyVariable"] * amount


def settle(c: dict, contested: bool) -> dict:
    if not contested:
        return {"recovered": 0, "contestCost": 0, "fp": 0, "win": False, "loss": False}
    if c["wouldWinIfContested"]:
        return {"recovered": c["disputedAmount"], "contestCost": c["contestCost"], "fp": 0, "win": True, "loss": False}
    return {"recovered": 0, "contestCost": c["contestCost"], "fp": _fp(c["disputedAmount"]), "win": False, "loss": True}


def _rules_only(c: dict) -> dict:
    amount = c["disputedAmount"]
    auth = c["features"]["authentication_completed"] == 1
    delivered = c["features"]["delivery_confirmed"] == 1
    complete = c["evidencePackage"]["mandatoryComplete"]
    if not complete:
        return {"auto": False, "review": True, "contest": False, "drop": False, "action": "mark_evidence_incomplete"}
    if amount >= 15000:
        return {"auto": False, "review": True, "contest": False, "drop": False, "action": "request_human_review"}
    if amount >= 1500 and (auth or delivered):
        return {"auto": True, "review": False, "contest": True, "drop": False, "action": "prepare_representment_draft"}
    return {"auto": False, "review": False, "contest": False, "drop": True, "action": "recommend_do_not_contest"}


def _ml_policy(c: dict) -> dict:
    a = c["policyDecision"]["recommendedAction"]
    if a == "prepare_representment_draft":
        return {"auto": True, "review": False, "contest": True, "drop": False, "action": a}
    if a in ("request_human_review", "mark_evidence_incomplete"):
        human = (
            c["evidencePackage"]["mandatoryComplete"]
            and c["prediction"]["expectedRecoveredValue"] > 0
            and c["prediction"]["fightWorthinessProbability"] >= 0.5
        )
        return {"auto": False, "review": True, "contest": human, "drop": not human, "action": a}
    return {"auto": False, "review": False, "contest": False, "drop": True, "action": a}


def strategy_decision(strategy: str, c: dict) -> dict:
    if strategy == "contest_nothing":
        return {"auto": False, "review": False, "contest": False, "drop": True, "action": "recommend_do_not_contest"}
    if strategy == "contest_everything":
        return {"auto": True, "review": False, "contest": True, "drop": False, "action": "prepare_representment_draft"}
    if strategy == "rules_only":
        return _rules_only(c)
    if strategy == "ml_policy":
        return _ml_policy(c)
    raise ValueError("Unknown evaluation strategy.")


def run_strategy(sid: str, label: str, cases: list[dict]) -> dict:
    contested = auto = review = drop = wins = losses = 0
    gross = cost = fp = tp = winnable = 0.0
    for c in cases:
        if c["wouldWinIfContested"]:
            winnable += 1
        d = strategy_decision(sid, c)
        if d["auto"]:
            auto += 1
        if d["review"]:
            review += 1
        if d["drop"]:
            drop += 1
        if d["contest"]:
            contested += 1
            s = settle(c, True)
            gross += s["recovered"]
            cost += s["contestCost"]
            fp += s["fp"]
            if s["win"]:
                wins += 1
                tp += 1
            if s["loss"]:
                losses += 1
    n = len(cases)
    return {
        "strategy": sid,
        "label": label,
        "cases": n,
        "contested": contested,
        "autoPrepared": auto,
        "humanReview": review,
        "doNotContest": drop,
        "wins": wins,
        "losses": losses,
        "grossRecovery": gross,
        "contestCost": cost,
        "falsePositiveCost": fp,
        "netValue": gross - cost - fp,
        "coverageRate": contested / n if n else 0,
        "precisionContest": tp / contested if contested else 0,
        "recallWinnable": tp / winnable if winnable else 0,
    }


def classification_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    if not y_true or len(y_true) != len(y_pred):
        raise ValueError("Classification requires one prediction per label and a nonempty sample.")
    k = len(CATEGORY_ORDER)
    confusion = [[0] * k for _ in range(k)]
    for yt, yp in zip(y_true, y_pred):
        confusion[CATEGORY_ORDER.index(yt)][CATEGORY_ORDER.index(yp)] += 1
    per_class = {}
    acc = 0
    f1s = []
    for i, lab in enumerate(CATEGORY_ORDER):
        tp = confusion[i][i]
        fp = sum(confusion[r][i] for r in range(k) if r != i)
        fn = sum(confusion[i][c] for c in range(k) if c != i)
        acc += tp
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_class[lab] = {"precision": precision, "recall": recall, "f1": f1, "support": y_true.count(lab)}
        f1s.append(f1)
    n = len(y_true)
    return {
        "accuracy": acc / n if n else 0,
        "macroF1": sum(f1s) / k,
        "perClass": per_class,
        "confusion": confusion,
        "labels": CATEGORY_ORDER,
    }


def _validate_forecasts(y: list[int], p: list[float]) -> None:
    if not y or len(y) != len(p):
        raise ValueError("Evaluation requires one probability per label and a nonempty sample.")
    if any(label not in (0, 1) for label in y):
        raise ValueError("Outcome labels must be binary.")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in p):
        raise ValueError("Probabilities must be finite values between zero and one.")


def brier(y: list[int], p: list[float]) -> float:
    _validate_forecasts(y, p)
    return sum((pi - yi) ** 2 for yi, pi in zip(y, p)) / len(y)


def roc_auc(y: list[int], p: list[float]) -> float:
    _validate_forecasts(y, p)
    if len(set(y)) != 2:
        raise ValueError("ROC-AUC requires both won and lost outcomes.")
    return float(roc_auc_score(y, p))


def pr_auc(y: list[int], p: list[float]) -> float:
    _validate_forecasts(y, p)
    if not any(y):
        raise ValueError("PR-AUC requires at least one won outcome.")
    # A threshold selects all equal scores together. Sorting ties by the true
    # outcome gives the evaluator information the model does not have.
    precision, recall, _ = precision_recall_curve(y, p)
    return float(auc(recall, precision))


def calibration_report(y: list[int], p: list[float]) -> dict:
    bins = []
    for i in range(10):
        lo, hi = i / 10, (i + 1) / 10
        idx = [j for j, v in enumerate(p) if lo <= v < hi or (i == 9 and v == 1)]
        if not idx:
            bins.append({"meanPred": (lo + hi) / 2, "meanActual": (lo + hi) / 2, "count": 0, "lower": lo, "upper": hi})
            continue
        mp = sum(p[j] for j in idx) / len(idx)
        ma = sum(y[j] for j in idx) / len(idx)
        bins.append({"meanPred": mp, "meanActual": ma, "count": len(idx), "lower": lo, "upper": hi})
    ece = sum(b["count"] * abs(b["meanPred"] - b["meanActual"]) for b in bins) / max(1, len(y))
    return {"brierScore": brier(y, p), "ece": ece, "bins": bins}


def build_evaluation(disputes: list[dict], selected_threshold: float, model_version: str, *, threshold_feasible: bool = True) -> dict:
    train = [c for c in disputes if c["split"] == "train"]
    valid = [c for c in disputes if c["split"] == "validation"]
    test = [c for c in disputes if c["split"] == "test"]
    classification = classification_metrics(
        [c["trueCategory"] for c in test],
        [c["prediction"]["predictedCategory"] for c in test],
    )
    y_win = [1 if c["wouldWinIfContested"] else 0 for c in test]
    p_win = [c["prediction"]["fightWorthinessProbability"] for c in test]
    pred_bin = [1 if p >= selected_threshold else 0 for p in p_win]
    tp = sum(1 for a, b in zip(pred_bin, y_win) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(pred_bin, y_win) if a == 1 and b == 0)
    fn = sum(1 for a, b in zip(pred_bin, y_win) if a == 0 and b == 1)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    curve = []
    for thr in sorted({selected_threshold, *(t / 100 for t in range(10, 91, 5))}):
        ctp = recov = fpc = net = contested = pos = 0
        for c in valid:
            if c["wouldWinIfContested"]:
                pos += 1
            contest = c["prediction"]["fightWorthinessProbability"] >= thr and c["evidencePackage"]["mandatoryComplete"]
            if not contest:
                continue
            contested += 1
            s = settle(c, True)
            recov += s["recovered"]
            fpc += s["fp"]
            net += s["recovered"] - s["contestCost"] - s["fp"]
            if s["win"]:
                ctp += 1
        curve.append(
            {
                "threshold": thr,
                "precision": ctp / contested if contested else 0,
                "recall": ctp / pos if pos else 0,
                "expectedRecovery": recov,
                "falsePositiveCost": fpc,
                "netValue": net,
                "contested": contested,
            }
        )
    operating = next(p for p in curve if p["threshold"] == selected_threshold)
    strategies = [
        run_strategy("contest_nothing", "Contest nothing", test),
        run_strategy("contest_everything", "Contest everything", test),
        run_strategy("rules_only", "Rules only", test),
        run_strategy("ml_policy", "ML + policy gate", test),
    ]
    gaps: dict[str, dict] = {}
    for c in disputes:
        for item in c["evidencePackage"]["items"]:
            if item["tier"] == "required" and not item["present"]:
                gaps.setdefault(item["key"], {"label": item["label"], "n": 0})
                gaps[item["key"]]["n"] += 1
    evidence_gaps = sorted(
        [{"key": k, "label": v["label"], "missingCount": v["n"]} for k, v in gaps.items()],
        key=lambda x: -x["missingCount"],
    )[:8]
    return {
        "nTrain": len(train),
        "nValid": len(valid),
        "nTest": len(test),
        "frozen": True,
        "seed": 42,
        "datasetVersion": DATASET_VERSION,
        "modelVersion": model_version,
        "selectedThreshold": selected_threshold,
        "thresholdRationale": (
            f"Selected on validation only. Maximize simulated net value subject to contest precision ≥ 75% "
            f"Frozen threshold = {selected_threshold:.2f} before any test-set look."
            if threshold_feasible else "No validation candidate met 75% precision. The reported 0.50 diagnostic threshold is a fallback, not an approved operating threshold; deterministic policy still gates every draft."
        ),
        "classification": classification,
        "fightWorthiness": {
            "prAuc": pr_auc(y_win, p_win),
            "rocAuc": roc_auc(y_win, p_win),
            "brier": brier(y_win, p_win),
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "supportPositive": sum(y_win),
        },
        "calibration": calibration_report(y_win, p_win),
        "thresholdCurve": curve,
        "strategies": strategies,
        "operatingPoint": operating,
        "evidenceGaps": evidence_gaps,
    }


def build_failure_gallery(disputes: list[dict]) -> list[dict]:
    test = [c for c in disputes if c["split"] == "test"]
    misses = [c for c in test if c["prediction"]["predictedCategory"] != c["trueCategory"]]
    misses.sort(key=lambda c: -c["prediction"]["categoryConfidence"])
    picked = []
    seen = set()
    for c in misses:
        key = f"{c['trueCategory']}->{c['prediction']['predictedCategory']}"
        if len(picked) >= 8:
            break
        if c["isDemo"] and c.get("demoRole") != "ambiguous_review":
            continue
        if key in seen and len(picked) >= 4:
            continue
        seen.add(key)
        picked.append(c)
    for c in misses:
        if len(picked) >= 8:
            break
        if c not in picked:
            picked.append(c)
    out = []
    for c in picked:
        policy_prevented = (not c["policyDecision"]["allowed"]) and (
            c["trueCategory"] in ("true_fraud_likely", "technical_or_insufficient_information") or not c["wouldWinIfContested"]
        )
        top = c["prediction"]["shap"][0] if c["prediction"]["shap"] else None
        signal = f"{top['label']} ({top['direction']})" if top else "mixed signals"
        out.append(
            {
                "caseId": c["id"],
                "trueCategory": c["trueCategory"],
                "predictedCategory": c["prediction"]["predictedCategory"],
                "confidence": c["prediction"]["categoryConfidence"],
                "topShap": c["prediction"]["shap"][:4],
                "whyFailed": f"The prediction disagreed with the synthetic category label. The measured top contribution was {signal}. Policy still has to approve any automatic draft.",
                "policyPreventedHarm": policy_prevented,
                "policyAction": c["policyDecision"]["recommendedAction"],
            }
        )
    return out


def overview_from(disputes: list[dict], ev: dict) -> dict:
    ml = next(s for s in ev["strategies"] if s["strategy"] == "ml_policy")
    queue = sum(1 for c in disputes if c["state"] in ("human_review", "evidence_incomplete"))
    auto = sum(1 for c in disputes if c["state"] in ("draft_ready", "submitted_simulated", "won_simulated", "lost_simulated"))
    return {
        "totalDisputes": len(disputes),
        "totalDisputedAmount": sum(c["disputedAmount"] for c in disputes),
        "potentialRecovery": sum(c["disputedAmount"] for c in disputes if c["wouldWinIfContested"]),
        "simulatedRecovered": ml["grossRecovery"],
        "netValue": ml["netValue"],
        "autoPrepRate": auto / len(disputes) if disputes else 0,
        "humanReviewQueue": queue,
        "modelPrecision": ev["fightWorthiness"]["precision"],
        "modelRecall": ev["fightWorthiness"]["recall"],
        "modelMacroF1": ev["classification"]["macroF1"],
        "falsePositiveCost": ml["falsePositiveCost"],
        "coverageRate": ml["coverageRate"],
        "heldOutN": ev["nTest"],
    }
