"""Prepare a local model and measured report without opening a database."""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
from pathlib import Path

from app.domain.generate import generate_world
from app.domain.model import load_model, train_model
from app.services.benchmark import benchmark, seed_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=1500)
    parser.add_argument("--report", type=Path, default=Path("ml/reports/benchmark.json"))
    parser.add_argument("--evaluate-only", action="store_true", help="Reuse the current matching artifact without retraining")
    args = parser.parse_args()
    if not 500 <= args.cases <= 5000:
        parser.error("--cases must be between 500 and 5000")
    bundle = load_model() if args.evaluate_only else train_model(generate_world(42, args.cases)["cases"])
    if bundle is None:
        parser.error("A matching model artifact is required for --evaluate-only")
    print("Model ready; measuring the frozen benchmark.", flush=True)
    scored, report = benchmark(bundle, 42, args.cases)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    args.report.with_name("seed_manifest.json").write_text(json.dumps(seed_manifest(scored, 42), indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.report), "modelVersion": bundle["modelVersion"],
                      "nTest": report["evaluation"]["nTest"], "strategies": report["evaluation"]["strategies"]}))


if __name__ == "__main__":
    main()
