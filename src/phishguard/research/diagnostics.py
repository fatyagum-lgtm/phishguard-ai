"""Post-hoc collection-bias diagnostics; never used to select models or thresholds."""

import pandas as pd

from phishguard.urls import parse_url


def collection_bias(train: pd.DataFrame) -> dict:
    """Describe shortcuts using the training partition only, without revisiting selection."""
    parsed = [parse_url(u) for u in train.url]
    view = pd.DataFrame(
        {
            "label": train.label.to_numpy(),
            "https": [u.scheme == "https" for u in parsed],
            "www_prefix": [u.host.startswith("www.") for u in parsed],
        }
    )
    by_label = []
    for label, group in view.groupby("label"):
        by_label.append(
            {
                "label": int(label),
                "rows": len(group),
                "https_fraction": float(group.https.mean()),
                "www_prefix_fraction": float(group.www_prefix.mean()),
            }
        )
    return {
        "scope": "Post-hoc diagnostic on domain-disjoint training data only",
        "used_for_model_selection": False,
        "by_label": by_label,
        "interpretation": (
            "Class-conditional formatting associations suggest collection bias; "
            "neither HTTPS nor www establishes safety. No causal claim is made."
        ),
    }
