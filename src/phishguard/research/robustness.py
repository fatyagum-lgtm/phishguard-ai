"""Offline input sensitivity, not demonstrations of malicious delivery or evasion."""

from urllib.parse import urlsplit, urlunsplit

import numpy as np

from phishguard.features import observations, rule_score
from phishguard.urls import defang, parse_url


def transform(value: str, category: str) -> str:
    p = urlsplit(value)
    if category == "host_case":
        userinfo, separator, authority = p.netloc.rpartition("@")
        return urlunsplit(
            (
                p.scheme.upper(),
                userinfo + separator + authority.upper(),
                p.path,
                p.query,
                p.fragment,
            )
        )
    if category == "unreserved_encoding":
        path = p.path
        for i, char in enumerate(path):
            if char.isascii() and char.isalpha():
                path = path[:i] + f"%{ord(char):02X}" + path[i + 1 :]
                break
        return urlunsplit((p.scheme, p.netloc, path, p.query, p.fragment))
    if category == "query_addition":
        return urlunsplit(
            (
                p.scheme,
                p.netloc,
                p.path,
                p.query + ("&" if p.query else "") + "pg_demo=1",
                p.fragment,
            )
        )
    if category == "path_extension":
        return urlunsplit((p.scheme, p.netloc, p.path.rstrip("/") + "/notice", p.query, p.fragment))
    if category == "subdomain_depth":
        return urlunsplit((p.scheme, "preview.eu." + p.netloc, p.path, p.query, p.fragment))
    if category == "scheme_switch":
        return urlunsplit(
            ("http" if p.scheme == "https" else "https", p.netloc, p.path, p.query, p.fragment)
        )
    if category == "www_prefix":
        return urlunsplit((p.scheme, "www." + p.netloc, p.path, p.query, p.fragment))
    raise ValueError("Unknown transformation.")


def synthetic_urls() -> list[str]:
    return [
        u
        for i in range(30)
        for u in (
            f"https://docs-{i}.example.test/articles/topic-{i}",
            f"http://account-verify-{i}.example.test/login/secure?user=demo{i}",
        )
    ]


def experiment(models: list[tuple], real_urls: list[str]) -> list[dict]:
    rows = []
    for category in [
        "host_case",
        "unreserved_encoding",
        "query_addition",
        "path_extension",
        "subdomain_depth",
        "scheme_switch",
        "www_prefix",
    ]:
        real = category in {"host_case", "unreserved_encoding"}
        original = real_urls[:400] if real else synthetic_urls()
        changed = [transform(u, category) for u in original]
        normal_original = [parse_url(u).normalized for u in original]
        normal_changed = [parse_url(u).normalized for u in changed]
        rule_changes = sum(
            {x["code"] for x in observations(parse_url(a))}
            != {x["code"] for x in observations(parse_url(b))}
            for a, b in zip(original, changed, strict=True)
        ) / len(original)
        for name, predict, threshold in models + [
            ("rules", lambda us: np.array([rule_score(parse_url(u)) for u in us]), 0.5)
        ]:
            before, after = predict(normal_original), predict(normal_changed)
            difference = after - before
            top = int(np.argmax(np.abs(difference)))
            rows.append(
                {
                    "category": category,
                    "exploratory": category in {"scheme_switch", "www_prefix"},
                    "model": name,
                    "n": len(original),
                    "scope": "real holdout, canonical representation check"
                    if real
                    else "reserved-domain synthetic inputs; no ground-truth claim",
                    "changed_inputs": sum(a != b for a, b in zip(original, changed, strict=True)),
                    "mean_absolute_delta": float(np.abs(difference).mean()),
                    "max_absolute_delta": float(np.abs(difference).max()),
                    "flip_rate": float(((before >= threshold) != (after >= threshold)).mean()),
                    "review_rate_before": float((np.abs(before - threshold) <= 0.1).mean()),
                    "review_rate_after": float((np.abs(after - threshold) <= 0.1).mean()),
                    "rule_finding_change_rate": rule_changes,
                    "example": {
                        "before": defang(original[top]),
                        "after": defang(changed[top]),
                        "score_before": float(before[top]),
                        "score_after": float(after[top]),
                    },
                }
            )
    return rows
