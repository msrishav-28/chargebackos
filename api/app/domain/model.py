from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from pickle import UnpicklingError

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.preprocessing import StandardScaler

from app.domain.constants import DATASET_VERSION, CATEGORY_ORDER, FEATURE_KEYS, FEATURE_LABELS, FEATURE_VERSION, MODEL_VERSION
from app.domain.policy import expected_value
from app.core.logging import log_event

ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "model.joblib"


def _xy(cases: list[dict]):
    x = np.array([[c["features"][k] for k in FEATURE_KEYS] for c in cases], dtype=float)
    y_cat = np.array([CATEGORY_ORDER.index(c["trueCategory"]) for c in cases], dtype=int)
    y_win = np.array([1 if c["wouldWinIfContested"] else 0 for c in cases], dtype=int)
    return x, y_cat, y_win


def train_model(cases: list[dict]) -> dict:
    train = [c for c in cases if c["split"] == "train"]
    valid = [c for c in cases if c["split"] == "validation"]
    x_tr, y_cat, y_win = _xy(train)
    x_va, y_cat_v, y_win_v = _xy(valid)
    scaler = StandardScaler()
    x_trs = scaler.fit_transform(x_tr)
    x_vas = scaler.transform(x_va)
    cat = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.08, max_iter=120, random_state=42)
    cat.fit(x_trs, y_cat)
    win = HistGradientBoostingClassifier(max_depth=5, learning_rate=0.08, max_iter=120, random_state=42)
    win.fit(x_trs, y_win)
    cat_cal = CalibratedClassifierCV(FrozenEstimator(cat), method="isotonic")
    cat_cal.fit(x_vas, y_cat_v)
    win_cal = CalibratedClassifierCV(FrozenEstimator(win), method="isotonic")
    win_cal.fit(x_vas, y_win_v)
    p_win = win_cal.predict_proba(x_vas)[:, 1]
    selected = 0.45
    best = -1e18
    for t in range(10, 81, 2):
        thr = t / 100
        net = 0.0
        tp = fp = 0
        for i, c in enumerate(valid):
            contest = p_win[i] >= thr and c["evidencePackage"]["mandatoryComplete"]
            if contest and c["wouldWinIfContested"]:
                tp += 1
                net += c["disputedAmount"] - c["contestCost"]
            elif contest and not c["wouldWinIfContested"]:
                fp += 1
                net -= c["contestCost"] + 900 + 0.1 * c["disputedAmount"]
        prec = tp / (tp + fp) if tp + fp else 0
        if prec >= 0.75 and net > best:
            best = net
            selected = thr
    if best == -1e18:
        selected = 0.5
    bundle = {
        "datasetVersion": DATASET_VERSION,
        "modelVersion": MODEL_VERSION,
        "featureVersion": FEATURE_VERSION,
        "scaler": scaler,
        "cat": cat,
        "win": win,
        "cat_cal": cat_cal,
        "win_cal": win_cal,
        "selectedThreshold": selected,
        "thresholdFeasible": best != -1e18,
        "explanationBaseline": np.median(x_trs, axis=0),
        "explanationMethod": "permutation-shapley-4-pairs-training-median",
        "nTrain": len(train), "nValid": len(valid), "nCases": len(cases),
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, ARTIFACT_PATH)
    return bundle


@lru_cache(maxsize=1)
def _load_artifact(path: str, modified: int) -> dict:
    bundle = joblib.load(path)
    if (not isinstance(bundle, dict) or bundle.get("modelVersion") != MODEL_VERSION
            or bundle.get("featureVersion") != FEATURE_VERSION
            or bundle.get("datasetVersion") != DATASET_VERSION
            or not {"cat_cal", "win_cal", "scaler", "explanationBaseline"}.issubset(bundle)):
        raise ValueError("Incompatible model artifact")
    return bundle


def load_model() -> dict | None:
    try:
        return _load_artifact(str(ARTIFACT_PATH), ARTIFACT_PATH.stat().st_mtime_ns)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, EOFError, UnpicklingError, KeyError, AttributeError, ImportError) as exc:
        log_event("model.unavailable", error_type=type(exc).__name__, model_version=MODEL_VERSION)
        return None


def permutation_contributions(predict, sample: np.ndarray, baseline: np.ndarray, pairs: int = 4) -> np.ndarray:
    """Approximate Shapley values against a fixed training-only reference.

    Forward/reverse permutations telescope to prediction minus baseline on
    every path. They describe model behavior, not causal effects.
    """
    rng = np.random.default_rng(42)
    paths, orders = [], []
    for _ in range(pairs):
        order = rng.permutation(len(sample))
        for indices in (order, order[::-1]):
            row = baseline.copy()
            paths.append(row.copy())
            for index in indices:
                row[index] = sample[index]
                paths.append(row.copy())
            orders.append(indices)
    scores = np.asarray(predict(np.asarray(paths))).reshape(len(orders), len(sample) + 1)
    contributions = np.zeros(len(sample))
    for order, values in zip(orders, scores):
        contributions[order] += np.diff(values)
    return contributions / len(orders)


def _attributions(bundle: dict, x_std: np.ndarray, pred_idx: int) -> list[dict]:
    contrib = permutation_contributions(
        lambda rows: bundle["cat_cal"].predict_proba(rows)[:, pred_idx],
        x_std, bundle["explanationBaseline"],
    )
    items = []
    for j, key in enumerate(FEATURE_KEYS):
        items.append(
            {
                "feature": key,
                "label": FEATURE_LABELS[key],
                "value": float(x_std[j]),
                "contribution": float(contrib[j]),
                "direction": "supports" if contrib[j] >= 0 else "opposes",
            }
        )
    items.sort(key=lambda s: abs(s["contribution"]), reverse=True)
    return items


def predict_case(bundle: dict, raw: dict) -> dict:
    x = np.array([[raw["features"][k] for k in FEATURE_KEYS]], dtype=float)
    xs = bundle["scaler"].transform(x)
    x_std = xs[0]
    proba = bundle["cat_cal"].predict_proba(xs)[0]
    pred_idx = int(np.argmax(proba))
    predicted = CATEGORY_ORDER[pred_idx]
    p_win = float(bundle["win_cal"].predict_proba(xs)[0, 1])
    conf = float(proba[pred_idx])
    ev = expected_value(p_win, raw["disputedAmount"], raw["contestCost"])
    scores = {lab: float(proba[i]) for i, lab in enumerate(CATEGORY_ORDER)}
    return {
        "modelVersion": bundle["modelVersion"],
        "featureVersion": bundle["featureVersion"],
        "predictedCategory": predicted,
        "categoryConfidence": conf,
        "classScores": scores,
        "fightWorthinessProbability": p_win,
        "expectedRecoveredValue": ev,
        "shap": _attributions(bundle, x_std, pred_idx),
        "calibrated": True,
    }
