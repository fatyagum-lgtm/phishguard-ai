"""Standalone scientific plots from actual persisted experiment artifacts."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def generate(report: dict, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    group = [m for m in report["models"] if m["protocol"] == "domain_disjoint"]
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.barh([m["model"] for m in group], [m["metrics"]["f1"] for m in group], color="#087e8b")
    ax.set(
        xlim=(0, 1),
        xlabel="Phishing-class F1 (held-out domains)",
        title="Model and feature-family comparison",
    )
    for i, m in enumerate(group):
        ax.text(m["metrics"]["f1"] + 0.008, i, f"{m['metrics']['f1']:.3f}", va="center")
    fig.savefig(destination / "model-comparison.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
    for m in group:
        if m["model"] not in {report["selected_model"], "rules"} and m["kind"] != "char":
            continue
        for i, key in enumerate(["pr", "roc"]):
            points = m["curves"][key]
            axes[i].plot([p[0] for p in points], [p[1] for p in points], label=m["model"])
        bins = m["metrics"]["reliability"]
        if bins:
            axes[2].plot(
                [b["mean_score"] for b in bins],
                [b["positive_fraction"] for b in bins],
                marker="o",
                markersize=3,
                label=m["model"],
            )
    axes[2].plot([0, 1], [0, 1], "--", color="gray", label="ideal")
    for ax, (title, x, y) in zip(
        axes,
        [
            ("Precision–recall", "Recall", "Precision"),
            ("ROC", "False-positive rate", "True-positive rate"),
            ("Reliability, 10 equal-width bins", "Mean estimate", "Phishing fraction"),
        ],
        strict=True,
    ):
        ax.set(title=title, xlabel=x, ylabel=y, xlim=(0, 1), ylim=(0, 1.02))
        ax.legend(fontsize=7)
    fig.savefig(destination / "discrimination-calibration.png", dpi=180)
    plt.close(fig)
    categories = list(dict.fromkeys(r["category"] for r in report["robustness"]))
    names = list(dict.fromkeys(r["model"] for r in report["robustness"]))
    fig, ax = plt.subplots(figsize=(9, 4), layout="constrained")
    for j, name in enumerate(names):
        values = [
            next(
                r["mean_absolute_delta"]
                for r in report["robustness"]
                if r["model"] == name and r["category"] == c
            )
            for c in categories
        ]
        ax.bar(np.arange(len(categories)) + j * 0.25, values, 0.24, label=name)
    ax.set(
        xticks=np.arange(len(categories)) + 0.25,
        xticklabels=[c.replace("_", "\n") for c in categories],
        ylabel="Mean absolute score change",
        title="Offline sensitivity; synthetic for noncanonical changes",
    )
    ax.legend(fontsize=8)
    fig.savefig(destination / "robustness.png", dpi=180)
    plt.close(fig)
