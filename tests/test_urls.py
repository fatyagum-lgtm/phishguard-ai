import socket

import numpy as np
import pytest

from phishguard.features import FEATURE_NAMES, extract, matrix, observations, rule_score
from phishguard.urls import InputError, parse_url


@pytest.mark.parametrize(
    "value",
    [
        "",
        "example.org",
        "/relative",
        "ftp://example.org",
        "javascript:alert(1)",
        "http://",
        "http://localhost",
        "http://127.1",
        "http://2130706433",
        "http://0x7f.0.0.1",
        "http://example.org:0",
        "http://example.org:99999",
        "http://example.org\\@evil.test",
        "http://example.org/\nfoo",
        "http://example.org/%zz",
        "http://a@b@example.org",
        "http://[fe80::1%25eth0]/",
        "http://example.org/" + "a" * 4096,
    ],
)
def test_invalid_urls(value):
    with pytest.raises(InputError):
        parse_url(value)


@pytest.mark.parametrize(
    "value,host",
    [
        ("https://bücher.de/x", "xn--bcher-kva.de"),
        ("HTTP://EXAMPLE.ORG:80/%7euser", "example.org"),
        ("https://192.0.2.1", "192.0.2.1"),
        ("https://[2001:db8::1]/", "2001:db8::1"),
    ],
)
def test_hosts(value, host):
    assert parse_url(value).host == host


def test_canonicalization_preserves_meaningful_parts():
    url = parse_url("HTTPS://Example.org:443/%7eA?token=%2f#Route")
    assert url.normalized == "https://example.org/~A?token=%2F#Route"
    assert url.fragment == "Route"
    assert parse_url(url.normalized).normalized == url.normalized


def test_private_suffix_groups():
    assert parse_url("https://one.github.io/a").domain == "one.github.io"
    assert parse_url("https://two.github.io/a").domain == "two.github.io"
    assert parse_url("https://a.b.example.co.uk").domain == "example.co.uk"


def test_no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Network access during URL analysis")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    import requests

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    assert parse_url("https://new-synthetic-host.example.org/test").domain == "example.org"


def test_features_consistent_and_rules_not_probability():
    value = "http://user@192.0.2.4/login/verify?q=demo"
    feature = extract(parse_url(value))
    x = matrix([value, value])
    assert x.shape == (2, len(FEATURE_NAMES))
    np.testing.assert_array_equal(x[0], x[1])
    assert feature["ip_host"] == feature["userinfo"] == 1
    assert rule_score(parse_url(value)) >= 0.5
    assert all(i["kind"] == "heuristic" for i in observations(parse_url(value)))
    assert parse_url("https://bücher.de").unicode_input


@pytest.mark.parametrize(
    "value",
    [
        "http://[::1]evil.org",
        "http://example.org:",
        "http://example.org..",
        "http://１２７.０.０.１/",
        "https://example.org/\ud800",
    ],
)
def test_ambiguous_authorities_and_invalid_unicode(value):
    with pytest.raises(InputError):
        parse_url(value)
