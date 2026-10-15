"""Measured discrimination and calibration; no fabricated uncertainty intervals."""

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def reliability(y: np.ndarray, scores: np.ndarray) -> tuple[list[dict], float]:
    bins, ece = [], 0.0
    assigned = np.minimum((scores * 10).astype(int), 9)
    for index in range(10):
        mask = assigned == index
        if not mask.any():
            continue
        mean, rate = float(scores[mask].mean()), float(y[mask].mean())
        count = int(mask.sum())
        ece += count / len(y) * abs(mean - rate)
        bins.append(
            {"mean_score": mean, "positive_fraction": rate, "count": count, "bin_lower": index / 10}
        )
    return bins, ece


def evaluate(y: np.ndarray, scores: np.ndarray, threshold: float, *, probability=True) -> dict:
    y, scores = np.asarray(y), np.asarray(scores)
    predicted = scores >= threshold
    tn, fp, fn, tp = map(int, confusion_matrix(y, predicted, labels=[0, 1]).ravel())
    both = len(np.unique(y)) == 2
    bins, ece = reliability(y, scores)
    return {
        "n": len(y),
        "threshold": threshold,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "fpr": fp / (fp + tn) if fp + tn else None,
        "fnr": fn / (fn + tp) if fn + tp else None,
        "roc_auc": float(roc_auc_score(y, scores)) if both else None,
        "average_precision": float(average_precision_score(y, scores)) if both else None,
        "brier": float(brier_score_loss(y, scores)) if probability else None,
        "ece": ece if probability else None,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "reliability": bins if probability else [],
    }


def curves(y: np.ndarray, scores: np.ndarray) -> dict:
    if len(np.unique(y)) != 2:
        return {"pr": [], "roc": []}
    precision, recall, _ = precision_recall_curve(y, scores)
    fpr, tpr, _ = roc_curve(y, scores)

    def points(x, y):
        indices = np.unique(np.linspace(0, len(x) - 1, min(101, len(x))).astype(int))
        return [[float(x[i]), float(y[i])] for i in indices]

    return {"pr": points(recall, precision), "roc": points(fpr, tpr)}


def select_threshold(y: np.ndarray, scores: np.ndarray) -> float:
    # Validation only. Coarse predeclared grid; ties prefer threshold nearest 0.5.
    values = np.linspace(0.1, 0.9, 81)
    return float(max(values, key=lambda t: (f1_score(y, scores >= t), -abs(t - 0.5))))


def bootstrap_f1(y, scores, groups, threshold, seed: int, repeats: int = 200) -> dict:
    """Resample whole registrable-domain clusters with replacement (conditional on fit)."""
    rng = np.random.default_rng(seed)
    unique, inverse = np.unique(groups, return_inverse=True)
    prediction = scores >= threshold
    # Per-cluster confusion counts avoid materializing repeated rows.
    tp = np.bincount(inverse, weights=(y == 1) & prediction)
    fp = np.bincount(inverse, weights=(y == 0) & prediction)
    fn = np.bincount(inverse, weights=(y == 1) & ~prediction)
    results = []
    for _ in range(repeats):
        sampled = rng.integers(0, len(unique), len(unique))
        a, b, c = tp[sampled].sum(), fp[sampled].sum(), fn[sampled].sum()
        if 2 * a + b + c:
            results.append(float(2 * a / (2 * a + b + c)))
    return {
        "method": "domain-cluster percentile bootstrap, conditional on fitted model",
        "repeats": repeats,
        "valid_repeats": len(results),
        "groups": len(unique),
        "low": float(np.quantile(results, 0.025)) if results else None,
        "high": float(np.quantile(results, 0.975)) if results else None,
    }
