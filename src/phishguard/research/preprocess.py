"""Deterministic cleaning and explicit partition leakage checks."""

import hashlib
import re
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from phishguard.urls import InputError, parse_url


def clean_rows(rows: list[tuple[str, int]]) -> tuple[pd.DataFrame, dict]:
    by_url: dict[str, dict] = {}
    rejected = Counter()
    for original, label in rows:
        try:
            u = parse_url(original)
        except (InputError, UnicodeError):
            rejected["unsupported_or_malformed"] += 1
            continue
        if u.normalized in by_url:
            by_url[u.normalized]["labels"].add(label)
            by_url[u.normalized]["count"] += 1
            continue
        # Diagnostic near-duplicate template only; not a semantic equivalence claim.
        template = (
            u.domain
            + re.sub(r"\d+", "#", u.path)
            + "?"
            + "&".join(sorted(q.split("=", 1)[0] for q in u.query.split("&") if q))
        )
        by_url[u.normalized] = {
            "original": original,
            "url": u.normalized,
            "domain": u.domain,
            "labels": {label},
            "count": 1,
            "id": hashlib.sha256(u.normalized.encode()).hexdigest(),
            "template": hashlib.sha256(template.encode()).hexdigest(),
        }
    records, conflicts, duplicates = [], 0, 0
    for item in by_url.values():
        count, labels = item.pop("count"), item.pop("labels")
        if len(labels) > 1:
            conflicts += count
        else:
            duplicates += count - 1
            records.append({**item, "label": next(iter(labels))})
    if not records:
        raise ValueError("Cleaning must leave samples of both classes.")
    frame = pd.DataFrame(records).sort_values("id").reset_index(drop=True)
    if frame.label.nunique() != 2:
        raise ValueError("Cleaning must leave samples of both classes.")
    info = {
        "input_rows": len(rows),
        "invalid_rows": sum(rejected.values()),
        "rejection_reasons": dict(rejected),
        "duplicate_rows_removed": duplicates,
        "conflicting_label_rows_removed": conflicts,
        "clean_rows": len(frame),
        "clean_domains": int(frame.domain.nunique()),
        "clean_classes": {str(k): int(v) for k, v in frame.label.value_counts().items()},
        "near_duplicate_template_rows": int(frame.template.duplicated().sum()),
    }
    return frame, info


def sample_rows(frame: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    if size < 100:
        raise ValueError("Use at least 100 samples.")
    if size >= len(frame):
        return frame.copy()
    chosen, _ = train_test_split(
        np.arange(len(frame)), train_size=size, stratify=frame.label, random_state=seed
    )
    return frame.iloc[chosen].sort_values("id").reset_index(drop=True)


def make_splits(frame: pd.DataFrame, protocol: str, seed: int) -> tuple[dict, dict]:
    if protocol not in {"random", "domain_disjoint"}:
        raise ValueError("Unknown evaluation protocol.")

    def split(indices: np.ndarray, fraction: float, offset: int):
        if protocol == "random":
            return train_test_split(
                indices,
                test_size=fraction,
                random_state=seed + offset,
                stratify=frame.label.iloc[indices],
            )
        splitter = GroupShuffleSplit(n_splits=1, test_size=fraction, random_state=seed + offset)
        a, b = next(splitter.split(indices, groups=frame.domain.iloc[indices]))
        return indices[a], indices[b]

    remainder, test = split(np.arange(len(frame)), 0.2, 0)
    remainder, calibration = split(remainder, 0.125, 1)
    train, validation = split(remainder, 1 / 7, 2)
    splits = dict(train=train, calibration=calibration, validation=validation, test=test)
    overlaps = []
    for a, b in combinations(splits, 2):
        left, right = frame.iloc[splits[a]], frame.iloc[splits[b]]
        exact = len(set(left.id) & set(right.id))
        domains = len(set(left.domain) & set(right.domain))
        if exact or (protocol == "domain_disjoint" and domains):
            raise ValueError("Partition leakage detected.")
        overlaps.append(
            {
                "pair": f"{a}/{b}",
                "exact_urls": exact,
                "domains": domains,
                "templates": len(set(left.template) & set(right.template)),
            }
        )
    for indices in splits.values():
        if frame.label.iloc[indices].nunique() != 2:
            raise ValueError("A partition lacks one class; do not silently change the seed.")
    details = {
        name: {
            "rows": len(ix),
            "domains": int(frame.domain.iloc[ix].nunique()),
            "phishing": int(frame.label.iloc[ix].sum()),
            "ids_sha256": hashlib.sha256("\n".join(frame.id.iloc[ix]).encode()).hexdigest(),
        }
        for name, ix in splits.items()
    }
    return splits, {"partitions": details, "overlaps": overlaps}
