"""A single URL interpretation contract for experiments and inference."""

import ipaddress
import re
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

import idna
import tldextract

MAX_URL = 4096
UNRESERVED = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
_PERCENT = re.compile(r"%([0-9a-fA-F]{2})")
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
# No first-use HTTP refresh and no disk cache. Version-locked bundled PSL, private included.
_PSL = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)


class InputError(ValueError):
    """Public, deliberately non-echoing validation error."""


@dataclass(frozen=True)
class ParsedURL:
    original: str
    normalized: str
    scheme: str
    host: str
    domain: str
    subdomain: str
    suffix: str
    port: int | None
    path: str
    query: str
    fragment: str
    is_ip: bool
    userinfo: bool
    unicode_input: bool


def _percent(value: str) -> str:
    def replace(match: re.Match) -> str:
        char = chr(int(match[1], 16))
        return char if char in UNRESERVED else "%" + match[1].upper()

    return _PERCENT.sub(replace, value)


@lru_cache(maxsize=8192)
def domain_parts(host: str) -> tuple[str, str, str]:
    part = _PSL(host)
    return part.top_domain_under_public_suffix or host, part.subdomain, part.suffix


def parse_url(value: str) -> ParsedURL:
    if not isinstance(value, str) or not value or len(value) > MAX_URL:
        raise InputError(f"Provide an absolute HTTP(S) URL of 1–{MAX_URL} characters.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise InputError("URL contains an invalid Unicode code point.") from exc
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value) or "\\" in value:
        raise InputError("Whitespace, control characters and backslashes are not supported.")
    if _BAD_PERCENT.search(value):
        raise InputError("Invalid percent escape in URL.")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            raise InputError("Only absolute http:// or https:// URLs are supported.")
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise InputError("Malformed URL authority or port.") from exc
    if not host or "%" in host or parts.netloc.count("@") > 1:
        raise InputError("Missing or ambiguous hostname.")
    authority_input = parts.netloc.rsplit("@", 1)[-1]
    # urlsplit accepts some bracket suffixes that browsers interpret differently.
    authority_pattern = r"\[[^\[\]]+\](?::[0-9]+)?" if ":" in host else r"[^:]+(?::[0-9]+)?"
    if not re.fullmatch(authority_pattern, authority_input):
        raise InputError("Ambiguous hostname or port syntax.")
    unicode_input = not host.isascii()
    host = host.removesuffix(".").lower()
    if host.endswith("."):
        raise InputError("Multiple trailing hostname dots are unsupported.")
    try:
        ip = ipaddress.ip_address(host)
        host, is_ip = ip.compressed, True
    except ValueError:
        is_ip = False
        # Browser alternate IPv4 syntax differs from RFC parsing: refuse ambiguity.
        if re.search(r"(?:^|\.)(?:[0-9]+|0x[0-9a-f]+)$", host):
            raise InputError("Ambiguous numeric hostname; use canonical IPv4 or IPv6.") from None
        try:
            host = idna.encode(host, uts46=True, std3_rules=True).decode("ascii")
        except idna.IDNAError as exc:
            raise InputError("Invalid internationalized hostname.") from exc
        if re.search(r"(?:^|\.)(?:[0-9]+|0x[0-9a-f]+)$", host):
            raise InputError("IDNA mapping produced an ambiguous numeric hostname.") from None
        if len(host) > 253 or "." not in host:
            raise InputError("A dotted hostname or canonical IP literal is required.") from None
    if port == 0:
        raise InputError("Port zero is not supported.")
    scheme = parts.scheme.lower()
    port = None if (scheme, port) in {("https", 443), ("http", 80)} else port
    authority = f"[{host}]" if ":" in host else host
    if port is not None:
        authority += f":{port}"
    userinfo = "@" in parts.netloc
    if userinfo:
        authority = _percent(parts.netloc.rsplit("@", 1)[0]) + "@" + authority
    path, query, fragment = map(_percent, (parts.path or "/", parts.query, parts.fragment))
    normalized = urlunsplit((scheme, authority, path, query, fragment))
    domain, subdomain, suffix = (host, "", "") if is_ip else domain_parts(host)
    return ParsedURL(
        value,
        normalized,
        scheme,
        host,
        domain,
        subdomain,
        suffix,
        port,
        path,
        query,
        fragment,
        is_ip,
        userinfo,
        unicode_input,
    )


def defang(value: str) -> str:
    """Readable, non-clickable research examples; not a cryptographic redaction."""
    return value.replace("https://", "hxxps://").replace("http://", "hxxp://").replace(".", "[.]")
