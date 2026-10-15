"""A complete, seeded experiment: choices on validation, final metrics on test."""

import hashlib
import importlib.metadata
import json
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from phishguard.features import FEATURE_NAMES, HOST_FEATURES, matrix, rule_score
from phishguard.model import PortableModel, save_model
from phishguard.research.data import EXPECTED_SHA256, read_archive
from phishguard.research.diagnostics import collection_bias
from phishguard.research.learners import Learner, candidates
from phishguard.research.metrics import bootstrap_f1, curves, evaluate, select_threshold
from phishguard.research.preprocess import clean_rows, make_splits, sample_rows
from phishguard.research.robustness import experiment
from phishguard.urls import defang, parse_url


def write_json(path: Path, value: dict | list):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n")


def latency(predict, urls: list[str]) -> dict:
    predict(urls[:5])
    durations = []
    for u in urls[:60]:
        start = time.perf_counter()
        predict([u])
        durations.append((time.perf_counter() - start) * 1000)
    batch = urls[:1000]
    start = time.perf_counter()
    predict(batch)
    elapsed = time.perf_counter() - start
    return {
        "n_single": len(durations),
        "mean_ms": float(np.mean(durations)),
        "median_ms": float(np.median(durations)),
        "p95_ms": float(np.quantile(durations, 0.95)),
        "batch_n": len(batch),
        "batch_seconds": elapsed,
        "batch_urls_per_second": len(batch) / elapsed,
    }


def error_examples(frame, scores: np.ndarray, threshold: float) -> list[dict]:
    result = []
    for kind, mask in [
        ("false_positive", (frame.label.to_numpy() == 0) & (scores >= threshold)),
        ("false_negative", (frame.label.to_numpy() == 1) & (scores < threshold)),
    ]:
        indices = np.flatnonzero(mask)
        indices = sorted(indices, key=lambda i: abs(float(scores[i]) - threshold), reverse=True)[:6]
        for i in indices:
            row = frame.iloc[i]
            result.append(
                {
                    "kind": kind,
                    "id": row.id,
                    "url_defanged": defang(row.url),
                    "label": int(row.label),
                    "score": float(scores[i]),
                }
            )
    return result


def run(archive: Path, output: Path, size=40000, seed=2026, smoke=False) -> dict:
    if output.exists():
        raise FileExistsError("Choose a new experiment output directory.")
    output.mkdir(parents=True)
    start = time.perf_counter()
    print("Cleaning verified UCI archive…", flush=True)
    frame, cleaning = clean_rows(read_archive(archive))
    frame = sample_rows(frame, size, seed)
    return run_frame(frame, cleaning, output, seed, smoke, start)


def run_frame(frame, cleaning, output: Path, seed=2026, smoke=False, start=None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter() if start is None else start
    results, manifest, choices, fitted = [], {}, {}, {}
    dataset = {
        **cleaning,
        "sample_rows": len(frame),
        "sample_domains": int(frame.domain.nunique()),
        "sample_phishing": int(frame.label.sum()),
        "archive_sha256": None if cleaning.get("synthetic") else EXPECTED_SHA256,
        "source": "Synthetic reserved-domain fixtures"
        if cleaning.get("synthetic")
        else "UCI PhiUSIIL 967",
        "license": "MIT (project fixtures)" if cleaning.get("synthetic") else "CC BY 4.0",
        "sample_id_sha256": hashlib.sha256("\n".join(frame.id).encode()).hexdigest(),
    }
    # Native BLAS single-threaded for reproducibility; forests explicitly use two workers.
    with threadpool_limits(limits=1):
        for protocol in ["random", "domain_disjoint"]:
            split, details = make_splits(frame, protocol, seed)
            manifest[protocol] = {k: frame.id.iloc[v].tolist() for k, v in split.items()}
            data = {k: frame.iloc[v].reset_index(drop=True) for k, v in split.items()}
            urls = {k: f.url.tolist() for k, f in data.items()}
            labels = {k: f.label.to_numpy() for k, f in data.items()}
            learned, validation = [], []
            for learner in candidates(smoke):
                print(f"{protocol}: fit {learner.name}", flush=True)
                learner.fit(urls["train"], labels["train"], seed, smoke)
                learner.calibrate(urls["calibration"], labels["calibration"])
                val_scores = learner.predict(urls["validation"])
                threshold = select_threshold(labels["validation"], val_scores)
                vm = evaluate(labels["validation"], val_scores, threshold)
                validation.append(
                    {
                        "model": learner.name,
                        "config": learner.config,
                        "metrics": vm,
                        "training_seconds": learner.training_seconds,
                    }
                )
                learned.append((learner, threshold, vm))

            # Selection completed BEFORE evaluating any final test scores.
            def rank(item):
                return (item[2]["f1"], -item[2]["brier"], -item[2]["fpr"])

            char = max([item for item in learned if item[0].kind == "char"], key=rank)
            forest = next(item for item in learned if item[0].name == "lexical_forest")
            selected = max([char, forest], key=rank)
            choices[protocol] = {
                **details,
                "validation_search": validation,
                "chosen": selected[0].name,
                "selection": "highest validation F1; ties lower Brier then FPR",
            }
            evaluated = [char, forest]
            if protocol == "domain_disjoint":
                for name, removed in [
                    ("forest_no_host", HOST_FEATURES),
                    ("forest_no_https", {"https"}),
                ]:
                    print(f"{protocol}: ablation {name}", flush=True)
                    learner = Learner(
                        name,
                        "forest",
                        {"removed": sorted(removed)},
                        [n for n in FEATURE_NAMES if n not in removed],
                    )
                    learner.fit(urls["train"], labels["train"], seed, smoke)
                    learner.calibrate(urls["calibration"], labels["calibration"])
                    ps = learner.predict(urls["validation"])
                    threshold = select_threshold(labels["validation"], ps)
                    evaluated.append(
                        (learner, threshold, evaluate(labels["validation"], ps, threshold))
                    )
            for learner, threshold, vm in evaluated:
                scores = learner.predict(urls["test"])
                metric = evaluate(labels["test"], scores, threshold)
                metric["f1_interval"] = bootstrap_f1(
                    labels["test"],
                    scores,
                    data["test"].domain.to_numpy(),
                    threshold,
                    seed,
                    50 if smoke else 200,
                )
                exported = {
                    "schema_version": 1,
                    "threshold": threshold,
                    "estimator": learner.export(),
                }
                native = PortableModel(exported)
                # Check all held-out predictions, not a single happy-path example.
                difference = float(np.max(np.abs(native.predict(urls["test"]) - scores)))
                if difference > 1e-10:
                    raise ValueError("Exported model diverges from sklearn inference.")
                results.append(
                    {
                        "protocol": protocol,
                        "model": learner.name,
                        "kind": learner.kind,
                        "metrics": metric,
                        "curves": curves(labels["test"], scores),
                        "validation": vm,
                        "training_seconds": learner.training_seconds,
                        "model_json_bytes": len(
                            json.dumps(exported, separators=(",", ":")).encode()
                        ),
                        "latency": latency(native.predict, urls["test"]),
                        "export_max_error": difference,
                        "raw_at_05": evaluate(
                            labels["test"], learner.predict(urls["test"], False), 0.5
                        ),
                        "calibrated_at_05": evaluate(labels["test"], scores, 0.5),
                        "errors": error_examples(data["test"], scores, threshold),
                    }
                )
            rule = np.array([rule_score(parse_url(u)) for u in urls["test"]])
            results.append(
                {
                    "protocol": protocol,
                    "model": "rules",
                    "kind": "heuristic",
                    "metrics": evaluate(labels["test"], rule, 0.5, probability=False),
                    "curves": curves(labels["test"], rule),
                }
            )
            if protocol == "domain_disjoint":
                fitted = {
                    "chosen": selected,
                    "train": urls["train"],
                    "test": urls["test"],
                    "models": [char, forest],
                    "diagnostics": collection_bias(data["train"]),
                }
        chosen, threshold, _ = fitted["chosen"]
        feature_matrix = matrix(fitted["train"])
        artifact = {
            "schema_version": 1,
            "version": "1.0.0",
            "model_id": chosen.name,
            "dataset": dataset,
            "threshold": threshold,
            "seed": seed,
            "protocol": "domain_disjoint",
            "review_margin": 0.1,
            "estimator": chosen.export(),
            "feature_min": feature_matrix.min(axis=0).tolist(),
            "feature_max": feature_matrix.max(axis=0).tolist(),
            "feature_names": list(FEATURE_NAMES),
            "scope": "synthetic smoke only"
            if cleaning.get("synthetic")
            else "URL-only UCI subset; not real-world incident probability",
        }
        model_bytes = save_model(output / "model.json", artifact)
        robust = experiment(
            [(m.name, m.predict, t) for m, t, _ in fitted["models"]], fitted["test"]
        )
    versions = {
        name: importlib.metadata.version(name)
        for name in ["numpy", "scipy", "pandas", "scikit-learn", "tldextract", "idna", "matplotlib"]
    }
    report = {
        "schema_version": 1,
        "generated_utc": datetime.now(UTC).isoformat(),
        "dataset": dataset,
        "seed": seed,
        "smoke": smoke,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "libraries": versions,
        },
        "protocols": choices,
        "models": results,
        "robustness": robust,
        "collection_bias": fitted["diagnostics"],
        "selected_model": chosen.name,
        "selected_artifact_bytes": model_bytes,
        "elapsed_seconds": time.perf_counter() - start,
        "limitations": [
            "Single-source URL-only subset; collection-time generalization untested.",
            (
                "Domain-disjoint is not campaign-disjoint. Near-duplicate "
                "templates are diagnostic only."
            ),
            (
                "Calibration reflects the held-out dataset distribution, not "
                "universal phishing probability."
            ),
            "Perturbations measure sensitivity, not exploitability or verified label preservation.",
            (
                "Bootstrap intervals condition on one fitted model and split; no "
                "retraining uncertainty."
            ),
        ],
    }
    write_json(output / "research.json", report)
    write_json(output / "split-manifest.json", manifest)
    print(f"Selected {chosen.name}; results: {output / 'research.json'}", flush=True)
    return report
