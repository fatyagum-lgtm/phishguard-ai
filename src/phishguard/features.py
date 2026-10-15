"""Offline features only. No UCI precomputed website or popularity attributes."""

import math
from collections import Counter

import numpy as np

from phishguard.urls import ParsedURL, parse_url

HOST_FEATURES = {
    "host_length",
    "subdomain_depth",
    "host_digit_ratio",
    "host_hyphens",
    "host_entropy",
    "ip_host",
    "punycode",
    "label_count",
    "max_label_length",
}
KEYWORDS = ("login", "verify", "secure", "account", "password", "update", "signin", "wallet")


def entropy(value: str) -> float:
    return -sum((n / len(value)) * math.log2(n / len(value)) for n in Counter(value).values())


def extract(url: ParsedURL) -> dict[str, float]:
    value, host = url.normalized, url.host
    labels = host.split(".")
    return {
        "url_length": float(len(value)),
        "host_length": float(len(host)),
        "https": float(url.scheme == "https"),
        "ip_host": float(url.is_ip),
        "userinfo": float(url.userinfo),
        "nondefault_port": float(url.port is not None),
        "subdomain_depth": float(len(url.subdomain.split(".")) if url.subdomain else 0),
        "label_count": float(len(labels)),
        "max_label_length": float(max(map(len, labels))),
        "host_digit_ratio": sum(c.isdigit() for c in host) / len(host),
        "host_hyphens": float(host.count("-")),
        "host_entropy": entropy(host),
        "punycode": float(any(x.startswith("xn--") for x in labels)),
        "path_length": float(len(url.path)),
        "path_segments": float(sum(bool(x) for x in url.path.split("/"))),
        "query_length": float(len(url.query)),
        "query_parameters": float(sum(bool(x) for x in url.query.split("&"))),
        "fragment_length": float(len(url.fragment)),
        "digit_ratio": sum(c.isdigit() for c in value) / len(value),
        "special_ratio": sum(not c.isalnum() for c in value) / len(value),
        "percent_count": float(value.count("%")),
        "at_count": float(value.count("@")),
        "hyphen_count": float(value.count("-")),
        "dot_count": float(value.count(".")),
        "keyword_count": float(sum(k in value.lower() for k in KEYWORDS)),
        "url_entropy": entropy(value),
    }


FEATURE_NAMES = tuple(extract(parse_url("https://example.org/")))


def matrix(urls: list[str], names: list[str] | tuple[str, ...] = FEATURE_NAMES) -> np.ndarray:
    features = [extract(parse_url(u)) for u in urls]
    return np.array([[f[n] for n in names] for f in features], dtype=np.float64)


def observations(url: ParsedURL) -> list[dict]:
    items = []
    checks = [
        (url.userinfo, "userinfo", "Authority includes user information before @", 2),
        (url.is_ip, "ip_host", "Hostname is an IP literal", 2),
        (url.scheme == "http", "unencrypted", "URL uses HTTP rather than HTTPS", 1),
        (len(url.normalized) > 120, "long_url", "Normalized URL exceeds 120 characters", 1),
        (
            len(url.subdomain.split(".")) >= 3 if url.subdomain else False,
            "deep_subdomain",
            "Three or more subdomain labels",
            1,
        ),
        (
            sum(k in url.normalized.lower() for k in KEYWORDS) >= 2,
            "sensitive_terms",
            "Multiple account/security terms appear in the URL",
            1,
        ),
        ("xn--" in url.host, "idn", "Internationalized domain encoding is present", 0),
        ("%" in url.normalized, "encoding", "Reserved percent-encoded bytes remain", 0),
    ]
    for condition, code, text, weight in checks:
        if condition:
            items.append(
                {
                    "code": code,
                    "message": text,
                    "weight": weight,
                    "kind": "heuristic",
                    "limitation": "Not proof of phishing.",
                }
            )
    return items


def rule_score(url: ParsedURL) -> float:
    """Fixed indicator index; NOT a probability. Positive at >= 0.5 (3 points)."""
    return min(sum(x["weight"] for x in observations(url)) / 6, 1.0)
