"""Compare splits, exported model and numerical metrics of two actual experiments."""

import argparse
import hashlib
import json
from pathlib import Path


def numeric_difference(left, right) -> float:
    if isinstance(left, dict):
        if left.keys() != right.keys():
            raise ValueError("Metric fields differ.")
        return max((numeric_difference(left[k], right[k]) for k in left), default=0)
    if isinstance(left, list):
        if len(left) != len(right):
            raise ValueError("Metric shapes differ.")
        return max((numeric_difference(a, b) for a, b in zip(left, right, strict=True)), default=0)
    if isinstance(left, int | float) and not isinstance(left, bool):
        return abs(left - right)
    if left != right:
        raise ValueError("Non-numerical metric value differs.")
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("reproduced", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [
        json.loads((p / "research.json").read_text()) for p in (args.reference, args.reproduced)
    ]
    same_dataset = reports[0]["dataset"] == reports[1]["dataset"]
    same_splits = (args.reference / "split-manifest.json").read_bytes() == (
        args.reproduced / "split-manifest.json"
    ).read_bytes()
    hashes = [
        hashlib.sha256((p / "model.json").read_bytes()).hexdigest()
        for p in (args.reference, args.reproduced)
    ]
    left = {(m["protocol"], m["model"]): m["metrics"] for m in reports[0]["models"]}
    right = {(m["protocol"], m["model"]): m["metrics"] for m in reports[1]["models"]}
    delta = numeric_difference(left, right)
    decisions_identical = all(
        left[key][field] == right[key][field]
        for key in left
        for field in ("threshold", "confusion_matrix", "precision", "recall", "f1", "fpr", "fnr")
    )
    # Forest parallel prediction reductions can perturb ties in rank metrics.
    # Record the discrepancy; do not claim bitwise forest reproducibility.
    passed = (
        same_dataset
        and same_splits
        and hashes[0] == hashes[1]
        and decisions_identical
        and delta < 1e-6
    )
    result = {
        "passed": passed,
        "same_dataset": same_dataset,
        "same_split_manifest": same_splits,
        "same_selected_model_bytes": hashes[0] == hashes[1],
        "model_sha256": hashes,
        "maximum_metric_absolute_difference": delta,
        "metric_tolerance": 1e-6,
        "decision_metrics_identical": decisions_identical,
        "strict_1e_minus_10_metric_check_passed": delta < 1e-10,
        "note": "Rank-metric drift retained; forests are not bitwise reproducible.",
        "excluded": [
            "wall-clock time",
            "latency",
            "generation time",
            "environment",
            "post-hoc diagnostics",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
