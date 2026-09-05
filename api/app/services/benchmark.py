from collections import Counter

from app.domain.constants import COST_ASSUMPTIONS, DATASET_VERSION, MODEL_VERSION, POLICY_VERSION
from app.domain.evaluation import build_evaluation, build_failure_gallery, overview_from
from app.domain.generate import generate_world
from app.domain.pipeline import score_raw


def seed_manifest(cases: list[dict], seed: int) -> dict:
    splits = Counter(case["split"] for case in cases)
    return {"seed": seed, "datasetVersion": DATASET_VERSION, "modelVersion": MODEL_VERSION,
            "policyVersion": POLICY_VERSION, "merchants": len({case["merchant"]["id"] for case in cases}),
            "disputes": len(cases), "nTrain": splits["train"], "nValid": splits["validation"], "nTest": splits["test"]}


def benchmark(bundle: dict, seed: int, target: int) -> tuple[list[dict], dict]:
    if seed != 42 or bundle["nCases"] != target:
        raise ValueError("The artifact must match the frozen seed-42 benchmark size.")
    world = generate_world(seed, target)
    totals = Counter(raw["merchant"]["id"] for raw in world["cases"])
    prepared = Counter()
    scored = []
    for raw in world["cases"]:
        merchant = raw["merchant"]["id"]
        case = score_raw(bundle, raw, auto_prep_rate=(prepared[merchant] + 1) / totals[merchant])
        prepared[merchant] += int(case["policyDecision"]["allowed"])
        scored.append(case)
    evaluation = build_evaluation(scored, bundle["selectedThreshold"], bundle["modelVersion"],
                                  threshold_feasible=bundle["thresholdFeasible"])
    return scored, {
        "evaluation": evaluation, "overview": overview_from(scored, evaluation),
        "failureGallery": build_failure_gallery(scored), "datasetVersion": DATASET_VERSION,
        "costAssumptions": {**COST_ASSUMPTIONS, "notes": "Synthetic INR cost model for evaluation only."},
    }
