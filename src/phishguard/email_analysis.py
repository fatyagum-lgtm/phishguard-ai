"""Bounded, offline RFC message inspection. Authentication headers are only claims."""

import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses
from html.parser import HTMLParser

from phishguard.urls import InputError, domain_parts, parse_url

MAX_EMAIL_BYTES = 256 * 1024
MAX_PARTS = 100
MAX_DEPTH = 12
MAX_URLS = 20
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links = [], []
        self.suppressed = 0
        self.anchor = None
        self.tags = 0

    def handle_starttag(self, tag: str, attrs):
        self.tags += 1
        if self.tags > 5000:
            raise InputError("HTML structure exceeds 5,000 tags.")
        if tag in {"script", "style", "iframe", "object", "template"}:
            self.suppressed += 1
        if tag == "a" and not self.suppressed:
            self.anchor = {"destination": dict(attrs).get("href", ""), "display": ""}
        if tag in {"p", "br", "div", "li"}:
            self.text.append("\n")

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "iframe", "object", "template"}:
            self.suppressed = max(0, self.suppressed - 1)
        if tag == "a" and self.anchor:
            self.links.append(self.anchor)
            self.anchor = None

    def handle_data(self, data: str):
        if not self.suppressed:
            self.text.append(data)
            if self.anchor:
                self.anchor["display"] += data


def _text(value: str, limit=2000) -> str:
    return "".join(c for c in str(value) if ord(c) >= 32 or c in "\n\t")[:limit]


def inspect_email(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_EMAIL_BYTES:
        raise InputError("Email must contain 1–262,144 bytes (256 KiB).")
    header = re.split(rb"\r?\n\r?\n", raw, maxsplit=1)[0]
    # Plain pasted text has no header block; bound individual lines regardless.
    if any(len(line) > 16384 for line in raw.splitlines()):
        raise InputError("Email contains a line longer than 16 KiB.")
    if header.splitlines() and b":" in header.splitlines()[0] and len(header) > 32768:
        raise InputError("Email header section exceeds 32 KiB.")
    count = 0

    def factory(*args, **kwargs):
        nonlocal count
        count += 1
        if count > MAX_PARTS:
            raise InputError("Email exceeds 100 MIME parts.")
        return EmailMessage(*args, **kwargs)

    try:
        message = BytesParser(_class=factory, policy=policy.default).parsebytes(raw)
        return _inspect_message(message)
    except InputError:
        raise
    except (ValueError, TypeError, RecursionError, LookupError, IndexError) as exc:
        raise InputError("Message structure could not be parsed safely.") from exc


def _inspect_message(message: EmailMessage) -> dict:
    bodies, anchors, attachments, defects = [], [], [], []
    stack = [(message, 0)]
    while stack:
        part, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise InputError("Email exceeds 12 nested MIME levels.")
        defects.extend(type(x).__name__ for x in part.defects)
        filename = part.get_filename()
        if filename or part.get_content_disposition() == "attachment":
            payload = part.get_payload()
            attachments.append(
                {
                    "name": _text(filename or "unnamed", 256),
                    "content_type": part.get_content_type(),
                    "encoded_characters": len(payload) if isinstance(payload, str) else None,
                    "opened": False,
                    "note": "Metadata only; payload not decoded or executed.",
                }
            )
            continue
        if part.is_multipart():
            stack.extend((child, depth + 1) for child in reversed(part.get_payload()))
            continue
        if part.get_content_type() not in {"text/plain", "text/html"}:
            continue
        decoded = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        try:
            text = decoded.decode(charset, errors="replace")
        except LookupError:
            text = decoded.decode("utf-8", errors="replace")
            defects.append("UnknownCharset")
        if part.get_content_type() == "text/html":
            html = TextHTML()
            html.feed(text)
            if html.anchor:
                html.links.append(html.anchor)
            anchors.extend(html.links)
            bodies.append("".join(html.text))
        else:
            bodies.append(text)
    body = "\n".join(bodies)
    from_headers = message.get_all("From", [])
    reply_headers = message.get_all("Reply-To", [])
    from_addresses = getaddresses([str(x) for x in from_headers])
    replies = getaddresses([str(x) for x in reply_headers])
    indicators = []

    def flag(code: str, detail: str):
        indicators.append({"code": code, "message": detail, "kind": "email_heuristic"})

    if len(from_headers) != 1 or len(from_addresses) != 1:
        flag("sender_structure", "Missing or multiple sender fields; identity is ambiguous.")
    if from_addresses and replies:
        source = from_addresses[0][1].rsplit("@", 1)[-1].lower()
        target = replies[0][1].rsplit("@", 1)[-1].lower()
        if domain_parts(source)[0] != domain_parts(target)[0]:
            flag("reply_to_difference", "Reply-To and From use different registrable domains.")
    for display, address in from_addresses:
        if "@" in display and display.strip().lower() != address.lower():
            flag(
                "display_address_difference",
                "An email-like display name differs from From address.",
            )
    if re.search(r"\b(urgent|immediately|suspended|within 24 hours|final warning)\b", body, re.I):
        flag("urgency", "Urgent or coercive language was observed (English keyword rule).")
    if re.search(
        r"\b(password|credentials|credit card|verify your account|one-time code)\b", body, re.I
    ):
        flag(
            "sensitive_request", "Language referencing credentials or sensitive data was observed."
        )
    for item in anchors:
        display, destination = item["display"].strip(), item["destination"]
        if display.lower().startswith(("https://", "http://")):
            try:
                if parse_url(display).host != parse_url(destination).host:
                    flag("link_mismatch", "A URL-like link label has a different destination host.")
            except InputError:
                flag(
                    "unsupported_link",
                    "A URL-like label is paired with an unsupported destination.",
                )
    if any(
        a["name"].lower().endswith((".exe", ".js", ".vbs", ".scr", ".html", ".zip"))
        for a in attachments
    ):
        flag(
            "attachment_extension",
            "Attachment names include executable, HTML or archive extensions.",
        )
    if defects:
        flag("mime_defects", "The MIME parser reported structural defects.")
    values = [m.group().rstrip(".,;!)]}") for m in URL_PATTERN.finditer(body)]
    values += [
        a["destination"]
        for a in anchors
        if a["destination"].lower().startswith(("http://", "https://"))
    ]
    unique = list(dict.fromkeys(values))
    claims = [_text(v) for v in message.get_all("Authentication-Results", [])[:10]]
    return {
        "subject": _text(message.get("Subject", "(no subject)")),
        "from": [
            {"display": _text(n, 256), "address": _text(a, 320)} for n, a in from_addresses[:10]
        ],
        "reply_to": [{"display": _text(n, 256), "address": _text(a, 320)} for n, a in replies[:10]],
        "received": [_text(v) for v in message.get_all("Received", [])[:10]],
        "authentication": {
            "verified": False,
            "reported_claims": claims,
            "note": (
                "These headers can be forged. SPF, DKIM and DMARC were NOT independently verified."
            ),
        },
        "body_text": _text(body, 12000),
        "body_truncated": len(body) > 12000,
        "attachments": attachments,
        "indicators": indicators,
        "defects": sorted(set(defects)),
        "urls": unique[:MAX_URLS],
        "url_count": len(unique),
        "urls_truncated": len(unique) > MAX_URLS,
        "method": (
            "Deterministic email indicators plus URL-level model inference; "
            "no trained email classifier."
        ),
    }
