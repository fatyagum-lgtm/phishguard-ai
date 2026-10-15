# Threat model

**Assets:** private messages/URLs, local filesystem, model integrity and accurate
interpretation of research claims. **Trust boundary:** everything submitted in a
message, URL, header or filename is untrusted. The operator, Python/Node runtimes
and locally installed application/model directory are trusted.

| Threat | Implemented boundary | Residual limitation |
|---|---|---|
| SSRF or live phishing contact | No submitted-URL retrieval or DNS; bundled offline PSL | Installation/acquisition are separate network operations |
| Active HTML / scripts | HTMLParser extracts text; React escapes strings; no dangerous HTML injection | Text may still contain deceptive wording or Unicode |
| Attachments / path traversal | `.eml` body stays in memory; filenames are metadata; no extraction | Attachment safety is not determined |
| Resource exhaustion | URL 4096 chars; message 256 KiB; 100 MIME parts, depth 12, 5000 HTML tags | Bounded parsing is not a formal sandbox or DoS proof |
| Hostile HTTP requests | 1 MiB total body, 1024 chunks, per-chunk 10 s timeout, local host/origin checks | No remote authentication or distributed rate limiting |
| Model injection | No upload-model endpoint; data-only schema, dimensions and numeric validation | Local checksum can be replaced with its model |
| Privacy leakage | No message persistence; access logging disabled; no-store/referrer/CSP headers | OS memory/swap, browser extensions and user exports remain outside scope |
| False trust | Dataset-calibrated scores and header claims explicitly qualified | Human decisions can still over-rely on a score |

Email lines are limited to 16 KiB and header sections to 32 KiB. Only 20 unique
URLs are analyzed, with truncation reported; body preview is 12,000 characters.
Only two analyses execute concurrently; the CLI server limits concurrency to 16.
No authentication means loopback access is the deployment boundary, not a user
identity boundary. Other local processes may call it. Do not publish a tunnel.

Guidance: [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html),
[Python email parser](https://docs.python.org/3/library/email.parser.html).
