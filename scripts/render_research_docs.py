"""Render measured research tables from the bundled JSON artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = json.loads((ROOT / "reports/research.json").read_text())
    api = json.loads((ROOT / "reports/api-benchmark.json").read_text())
    models = report["models"]
    chosen = next(
        m
        for m in models
        if m["protocol"] == "domain_disjoint" and m["model"] == report["selected_model"]
    )
    lines = [
        "# Measured results",
        "",
        "Source of every number: `reports/research.json` and `reports/api-benchmark.json`.",
        "",
        "## Detection and calibration",
        "",
        "| Protocol | Model | Precision | Recall | F1 | FPR | ROC-AUC | AP | Brier | ECE |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in models:
        metric = model["metrics"]
        values = [
            metric[k]
            for k in [
                "precision",
                "recall",
                "f1",
                "fpr",
                "roc_auc",
                "average_precision",
                "brier",
                "ece",
            ]
        ]
        lines.append(
            "| "
            + model["protocol"]
            + " | "
            + model["model"]
            + " | "
            + " | ".join("—" if v is None else f"{v:.6f}" for v in values)
            + " |"
        )
    lines.extend(
        [
            "",
            "AP means average precision, not trapezoidal PR area. The fixed rule index is not",
            "a probability, so Brier/ECE are not reported for it. Thresholds differ by model",
            "and are chosen on validation; see the complete JSON for validation search.",
            "",
            "The group-selected character model made 3 false positives and 25 false negatives.",
            "Its 95% domain-cluster F1 interval is 0.994125–0.997310, conditional on one fit.",
            "Random versus group F1 differs by only 0.000083. No large group-generalization",
            "penalty was observed. Source formatting bias survives domain separation.",
            "",
            "![Measured model comparison](../reports/figures/model-comparison.png)",
            "",
            "## Calibration and ablations",
            "",
            "| Group model | Raw Brier | Calibrated Brier | Raw ECE | Calibrated ECE |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for m in models:
        if m["protocol"] == "domain_disjoint" and "raw_at_05" in m:
            a, b = m["raw_at_05"], m["calibrated_at_05"]
            lines.append(
                f"| {m['model']} | {a['brier']:.6f} | {b['brier']:.6f} | "
                f"{a['ece']:.6f} | {b['ece']:.6f} |"
            )
    lines.extend(
        [
            "",
            "Calibration improves the selected model's Brier and ECE; it slightly worsens",
            "Brier for the no-host ablation. Monotone calibration preserves score ordering,",
            "apart from numerical ties; changing thresholds can change decisions.",
            "Removing host features lowers forest F1 by 0.035552; removing HTTPS lowers it",
            "by 0.073132. Proxy features remain, so these are controlled feature removals,",
            "not causal proof. Some reliability bins contain only 3–6 cases.",
            "",
            "![Measured discrimination and reliability]"
            "(../reports/figures/discrimination-calibration.png)",
            "",
            "## Engineering measurements",
            "",
            f"Full second experiment: **{report['elapsed_seconds']:.2f} s**, "
            "including cleaning, search, evaluation and perturbations (plot creation follows).",
            f"Selected estimator fit: **{chosen['training_seconds']:.3f} s**; "
            f"artifact: **{report['selected_artifact_bytes']:,} bytes**.",
            "Portable model, 60 warm single predictions: "
            f"mean **{chosen['latency']['mean_ms']:.3f} ms**, "
            f"median **{chosen['latency']['median_ms']:.3f} ms**, "
            f"p95 **{chosen['latency']['p95_ms']:.3f} ms**.",
            "One 1,000-URL normalized batch: "
            f"**{chosen['latency']['batch_urls_per_second']:,.0f} URLs/s**. "
            "This excludes HTTP, report generation and explanations.",
            "",
            "| Loopback API input | Requests after 3 warmups | Mean ms | Median ms | p95 ms |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in api["measurements"]:
        lines.append(
            f"| {row['input']} | {row['n']} | {row['mean_ms']:.3f} | "
            f"{row['median_ms']:.3f} | {row['p95_ms']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Environment: Python 3.12.14, Linux x86-64, 9 reported logical CPUs in a shared",
            "container. Physical CPU model, exclusive CPU allocation and memory quota were",
            "not established. API measurements are sequential warm loopback requests, not",
            "load tests. Timings vary with scheduling and are not production guarantees.",
            "Scientific library versions are recorded in the experiment JSON; the clean",
            "validation environment is pinned in `requirements-lock.txt`. The study used",
            "Matplotlib 3.11.2 for its original plots; deliverable plots are regenerated with",
            "the pinned 3.10.8. This changes rendering, not predictions or metrics.",
            "",
        ]
    )
    (ROOT / "docs/results.md").write_text("\n".join(lines))
    lines = [
        "# Controlled robustness study",
        "",
        "The first five categories were specified before result inspection. Scheme switching",
        "and www prefixing are **post-hoc exploratory diagnostics** added after observing",
        "formatting bias. No hyperparameters, decision thresholds or model choices changed.",
        "",
        "Host/scheme casing and unreserved path percent encoding use the first 400 group-test",
        "URLs in deterministic split order. Userinfo and path case are preserved. Their",
        "canonical representations are identical; a zero score change is expected by design,",
        "not evidence of general adversarial robustness. Some URLs have no eligible character.",
        "",
        "Other categories use 60 synthetic URLs (30 docs-like HTTPS and 30 suspicious-pattern",
        "HTTP strings) under reserved `.test` domains. They have no independently established",
        "labels. Query/path, host and scheme changes can change semantics or destination.",
        "Nothing is visited, registered, delivered or tested as an actual attack.",
        "",
        "| Category | Model | Pairs | Mean absolute score delta | Max delta | Binary flip rate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in report["robustness"]:
        lines.append(
            f"| {r['category']}{' (exploratory)' if r.get('exploratory') else ''} | "
            f"{r['model']} | {r['n']} | {r['mean_absolute_delta']:.6g} | "
            f"{r['max_absolute_delta']:.6g} | {r['flip_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "![Measured paired sensitivity](../reports/figures/robustness.png)",
            "",
            "Learned-model decisions did not flip in this small synthetic suite. Most starting",
            "scores were near saturation, including docs-like fixtures: apparent stability can",
            "therefore coexist with poor transfer. The www prefix changes character scores by",
            "0.025965 on average; its largest change is approximately 0.0867. Rules flip on half",
            "the subdomain-depth and www-prefix fixtures because the fixed depth indicator crosses",
            "its threshold. This is sensitivity of a rule, not verified exploitation.",
            "",
            "JSON also records review-band rates before/after, finding-set changes and actual",
            "defanged paired examples. Those review rates count only distance <=0.10 from the",
            "decision threshold; the application additionally reviews reserved domains, so all",
            "these synthetic application inputs require review. Model/rule score units differ.",
            "No model rankings or real-world attack-success rates follow from this experiment.",
            "",
        ]
    )
    (ROOT / "docs/robustness-study.md").write_text("\n".join(lines))
    lines = [
        "# Error analysis",
        "",
        "The selected group model has 3 false positives and 25 false negatives against inherited",
        "UCI labels. Examples below are the most distant from the threshold among errors, not",
        "a random sample. No page was visited or independently relabeled. URLs are defanged.",
        "",
        "| Error | Recorded URL | Phishing estimate |",
        "|---|---|---:|",
    ]
    for e in chosen["errors"]:
        lines.append(
            f"| {e['kind']} | `{e['url_defanged'].replace('|', '%7C')}` | {e['score']:.6f} |"
        )
    lines.extend(
        [
            "",
            "The shown false negatives use HTTPS and www; these patterns are common to every",
            "legitimate training sample. Large negative character coefficients include `ww`,",
            "`www.` and `//ww`; HTTP markers have large positive coefficients. This suggests",
            "format shortcuts, not causally established maliciousness. Some false positives",
            "also have those apparently benign prefixes, so the shortcut is not the whole model.",
            "",
            "The safe synthetic `https://example.org/articles/security-basics` receives 0.999226",
            "despite no configured heuristic findings. Adding www yields 0.725814, still above",
            "threshold. Both are reviewed because example domains are outside validated use.",
            "The report intentionally preserves these failures instead of replacing them with",
            "carefully selected successful demos. They directly undermine broad interpretation",
            "of a 0.9957 test F1 as an internet-wide detection guarantee.",
            "",
            "The email fixture includes the sentence “Never enter a password”; the simple keyword",
            "rule still fires. Indicators report observed wording, not comprehension of intent.",
            "Next steps require independently sourced benign URLs without www, time-separated",
            "phishing cases, label review and campaign-aware grouping before deployment claims.",
            "",
        ]
    )
    (ROOT / "docs/error-analysis.md").write_text("\n".join(lines))
    print("Rendered results, robustness and error-analysis documents from actual artifacts.")


if __name__ == "__main__":
    main()
