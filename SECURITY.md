# Security policy

PhishGuard AI 1.0 is a local research application, not a production security
gateway. Bind only to loopback. Do not expose it through a public tunnel or
reverse proxy; there is no user authentication or multi-tenant isolation.

Submitted URLs are never retrieved. Email HTML is reduced to text; attachment
payloads are not decoded, opened or executed. Analysis inputs remain in memory
and are not written to server history. Exported JSON contains the submitted
content: review it before sharing. The OS, browser, swap and extensions remain
outside the application's privacy boundary.

Only load model artifacts produced by this project from a directory you trust.
JSON avoids executable pickle deserialization; its adjacent checksum detects
accidental damage, not malicious replacement of both files.

For a suspected vulnerability, privately contact the repository owner through
their published profile or GitHub's private vulnerability reporting if enabled.
No reporting mailbox or response SLA is claimed. Include the version, minimal
synthetic reproduction, expected behavior and actual behavior. Do not include
private messages, credentials or active malicious links in public issues.

See [the threat model](docs/threat-model.md) and
[validation record](docs/validation.md). Dependency audit results are a dated
observation, not a guarantee that the application is free of vulnerabilities.
