# Synthetic demonstration

All example addresses are reserved domains. No URL is fetched. From the
installed repository root:

```bash
python scripts/demo.py
python -m phishguard.cli url 'https://example.org/articles/security-basics'
python -m phishguard.cli url 'http://account-verify.example.test/login/secure?user=demo'
python -m phishguard.cli email examples/message.eml
```

The first URL looks benign but receives a high model estimate. This is retained
as a useful failure case: the model learned strong source-format associations.
Both URL demonstrations require review because reserved domains are outside
validated use. Adding `www` changes the estimate; neither result proves intent.

The synthetic email demonstrates a display/address difference, different
Reply-To domain, urgency, credential-related wording, mismatched link text and
forged `Authentication-Results` claims. It has no functional phishing payload.
The email has no trained email probability; URL scores and email rules are
reported separately. Actual generated JSON is in `reports/demo/`.
