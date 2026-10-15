import pytest

from phishguard.email_analysis import MAX_EMAIL_BYTES, inspect_email
from phishguard.service import analyze_email
from phishguard.urls import InputError


def test_plain_text_without_headers():
    result = inspect_email(b"Hello, read https://example.org for details.")
    assert result["urls"] == ["https://example.org"]
    assert result["subject"] == "(no subject)"


def test_encoded_subject_and_forged_authentication():
    raw = (
        b"From: sender@example.org\nSubject: =?utf-8?b?VGVzdCDigJQ=?=\n"
        b"Authentication-Results: attacker.test; spf=pass; dkim=pass\n\nHello"
    )
    result = inspect_email(raw)
    assert result["subject"] == "Test —"
    assert result["authentication"]["verified"] is False
    assert "spf=pass" in result["authentication"]["reported_claims"][0]


def test_html_injection_link_mismatch_and_reply_to():
    raw = b"""From: "boss@example.org" <other@example.test>
Reply-To: receiver@example.invalid
Content-Type: text/html

<script>alert('owned')</script><img src="https://example.invalid/tracker">
<p>Urgent: verify your account password immediately.</p>
<a href="http://verify.example.test/login">https://example.org</a>"""
    result = inspect_email(raw)
    assert "alert" not in result["body_text"]
    assert "<img" not in result["body_text"]
    codes = {x["code"] for x in result["indicators"]}
    assert {
        "link_mismatch",
        "reply_to_difference",
        "display_address_difference",
        "urgency",
    } <= codes
    assert "https://example.invalid/tracker" not in result["urls"]


def test_attachment_payload_is_not_decoded():
    raw = b"""MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=x

--x
Content-Type: text/plain

Hello https://example.org
--x
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="../../payload.exe"
Content-Transfer-Encoding: base64

!!!invalid base64!!!
--x--
"""
    result = inspect_email(raw)
    assert result["attachments"][0]["opened"] is False
    assert result["attachments"][0]["name"] == "../../payload.exe"
    assert "InvalidBase64" not in " ".join(result["defects"])


def test_duplicate_sender_and_malformed_mime():
    raw = (
        b"From: a@example.org\nFrom: b@example.org\n"
        b"Content-Type: multipart/mixed; boundary=x\n\nmissing boundary"
    )
    result = inspect_email(raw)
    assert result["defects"]
    assert any(i["code"] == "sender_structure" for i in result["indicators"])


@pytest.mark.parametrize("raw", [b"", b"x" * (MAX_EMAIL_BYTES + 1), b"x" * 17000])
def test_size_limits(raw):
    with pytest.raises(InputError):
        inspect_email(raw)


def test_many_parts_and_deep_nesting():
    raw = (
        b"Content-Type: multipart/mixed; boundary=x\n\n"
        + (b"--x\nContent-Type: text/plain\n\nx\n" * 101)
        + b"--x--"
    )
    with pytest.raises(InputError, match="100 MIME"):
        inspect_email(raw)
    text = "Content-Type: text/plain\n\nx"
    for i in range(15):
        text = f"Content-Type: multipart/mixed; boundary=b{i}\n\n--b{i}\n{text}\n--b{i}--\n"
    with pytest.raises(InputError, match="nested"):
        inspect_email(text.encode())


def test_url_limit_and_no_email_model(model):
    result = analyze_email(
        (
            "From: a@example.org\n\n" + " ".join(f"https://example.org/{i}" for i in range(25))
        ).encode(),
        model,
    )
    assert result["url_count"] == 25 and len(result["url_reports"]) == 20
    assert result["urls_truncated"]
    assert "no trained email" in result["method"]
    assert "score" not in result
