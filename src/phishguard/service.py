"""Investigation reports distinguish observations, learned signals and uncertainty."""

import hashlib
import time
from dataclasses import asdict
from datetime import UTC, datetime

from phishguard.email_analysis import inspect_email
from phishguard.features import FEATURE_NAMES, extract, observations, rule_score
from phishguard.model import PortableModel
from phishguard.urls import InputError, parse_url


def analyze_url(value: str, model: PortableModel | None) -> dict:
    start = time.perf_counter()
    url = parse_url(value)
    features = extract(url)
    reasons = []
    score, binary, explanation, model_id = None, None, None, None
    classification = "review_required"
    if model:
        score = float(model.predict([url.normalized])[0])
        threshold = model.data["threshold"]
        binary = "phishing" if score >= threshold else "legitimate"
        model_id = model.data.get("model_id", model.spec["name"])
        if abs(score - threshold) <= model.data.get("review_margin", 0.1):
            reasons.append(
                "Score is within the configured review band around the decision threshold."
            )
        if (
            not url.suffix
            or url.host.endswith((".test", ".example", ".invalid"))
            or url.domain in {"example.org", "example.net", "example.com"}
        ):
            reasons.append(
                "No recognized public suffix or reserved example domain; outside validated use."
            )
        bounds = zip(
            FEATURE_NAMES,
            model.data.get("feature_min", []),
            model.data.get("feature_max", []),
            strict=False,
        )
        outliers = [n for n, low, high in bounds if not low <= features[n] <= high]
        if len(outliers) >= 3:
            reasons.append("At least three lexical features fall outside observed training ranges.")
        if not reasons:
            classification = "likely_" + binary
        explanation = model.explain(url.normalized)
    else:
        reasons.append(
            "No validated model is installed. Only observable features and rules are available."
        )
    return {
        "schema_version": 1,
        "kind": "url",
        "generated_utc": datetime.now(UTC).isoformat(),
        "input": asdict(url),
        "input_sha256": hashlib.sha256(value.encode()).hexdigest(),
        "classification": classification,
        "binary_model_label": binary,
        "score": score,
        "threshold": model.data["threshold"] if model else None,
        "score_meaning": (
            "Calibrated estimate on the evaluation distribution; not "
            "universal incident probability."
        ),
        "model_id": model_id,
        "model_version": model.data.get("version") if model else None,
        "review_reasons": reasons,
        "observed_features": features,
        "heuristics": observations(url),
        "rule_index": rule_score(url),
        "explanation": explanation,
        "analysis_ms": (time.perf_counter() - start) * 1000,
        "limitations": [
            "No page visit, DNS lookup, reputation check or sender verification occurred.",
            (
                "False positives and false negatives are possible. HTTPS and "
                "unusual names prove neither safety nor phishing."
            ),
            "The training dataset has strong HTTPS/www formatting bias; "
            "high scores may reflect that bias, even on benign-looking inputs.",
        ],
    }


def analyze_email(raw: bytes, model: PortableModel | None) -> dict:
    result = inspect_email(raw)
    reports = []
    for value in result.pop("urls"):
        try:
            reports.append({"url": value, "analysis": analyze_url(value, model), "error": None})
        except InputError as exc:
            reports.append({"url": value[:4096], "analysis": None, "error": str(exc)})
    result.update(
        {
            "kind": "email",
            "schema_version": 1,
            "generated_utc": datetime.now(UTC).isoformat(),
            "bytes": len(raw),
            "input_sha256": hashlib.sha256(raw).hexdigest(),
            "url_reports": reports,
            "classification": "review_required"
            if result["indicators"]
            or any(
                r["error"] or r["analysis"]["classification"] != "likely_legitimate"
                for r in reports
            )
            else "no_indicators_detected",
            "limitations": [
                "Email indicators are deterministic rules, not a trained email classifier.",
                (
                    "No indicators detected does not establish legitimacy. Header "
                    "claims are unverified."
                ),
                (
                    "Attachments and external resources were not opened; language "
                    "rules cover English only."
                ),
            ],
        }
    )
    return result
