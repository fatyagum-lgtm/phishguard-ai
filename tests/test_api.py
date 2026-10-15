import pytest
from conftest import ROOT
from fastapi.testclient import TestClient

from phishguard.api import create_app


@pytest.fixture
def client():
    with TestClient(create_app(model_path=ROOT / "models/model.json")) as client:
        yield client


def test_api_actual_prediction_and_model_info(client):
    assert client.get("/api/health").json()["model_available"]
    result = client.post("/api/analyze/url", json={"url": "https://example.org/article"})
    assert result.status_code == 200
    assert result.json()["model_id"] == client.get("/api/model/info").json()["model_id"]
    assert result.json()["score"] is not None
    assert "default-src 'self'" in result.headers["content-security-policy"]
    assert client.get("/api/research/summary").json()["dataset"]["sample_rows"] == 40000
    assert client.get("/api/research/experiments").json()["robustness"]


def test_no_private_content_in_errors(client):
    secret = "PRIVATE_EMAIL_SECRET"
    result = client.post("/api/analyze/url", json={"url": 14, "private": secret})
    assert result.status_code == 422 and secret not in result.text
    result = client.post("/api/analyze/url", json={"url": "javascript:" + secret})
    assert result.status_code == 422 and secret not in result.text


def test_request_boundaries_and_origin(client):
    assert client.post("/api/analyze/url", content=b"x" * (1024 * 1024 + 1)).status_code == 413
    assert client.post("/api/analyze/email", json={"content": "x" * 262145}).status_code == 422
    assert (
        client.post(
            "/api/analyze/url",
            headers={"Origin": "https://untrusted.example"},
            json={"url": "https://example.org"},
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
    assert client.post("/api/analyze/url", headers={"Content-Encoding": "gzip"}).status_code == 415


def test_email_file_and_paste(client):
    raw = b"From: a@example.org\nAuthentication-Results: fake; spf=pass\n\nRead https://example.org"
    result = client.post(
        "/api/analyze/email-file",
        content=raw,
        headers={"X-Filename": "sample.eml", "Content-Type": "message/rfc822"},
    )
    assert result.status_code == 200
    assert not result.json()["authentication"]["verified"]
    assert result.json()["url_reports"][0]["analysis"]["score"] is not None
    assert client.post("/api/analyze/email", json={"content": raw.decode()}).status_code == 200
    assert (
        client.post(
            "/api/analyze/email-file",
            content=raw,
            headers={"X-Filename": "../x.eml", "Content-Type": "message/rfc822"},
        ).status_code
        == 415
    )


def test_without_model_and_research(tmp_path):
    client = TestClient(
        create_app(model_path=tmp_path / "absent", research_path=tmp_path / "missing")
    )
    assert not client.get("/api/model/info").json()["available"]
    assert (
        client.post("/api/analyze/url", json={"url": "https://example.org"}).json()["score"] is None
    )
    assert client.get("/api/research/summary").status_code == 404
