# Architecture

The application has one local process and a static React client. FastAPI serves
compiled assets and `/api` on loopback; Vite's development proxy uses the same API.
There are no background crawlers, cloud dependencies or database/history layer.

| Component | Responsibility |
|---|---|
| `urls.py`, `features.py` | Shared strict URL interpretation and 26 offline features |
| `email_analysis.py` | Bounded MIME inspection, HTML-to-text and independent indicators |
| `model.py` | Validated data-only JSON inference and model-specific explanations |
| `service.py` | Investigation reports, uncertainty reasons, timestamps and input hashes |
| `api.py`, `cli.py` | Typed HTTP boundary and explicit local commands |
| `research/` | Verified acquisition, clean splits, training, calibration and evaluation |
| `frontend/src/` | Five screens reading actual API results and experiment artifacts |

The character artifact stores vocabulary, IDF, coefficients and sigmoid parameters.
Forest artifacts store bounded tree arrays. Every exported estimator is compared
with sklearn on all final holdout inputs, with maximum difference below 1e-10.
No executable pickle/joblib is loaded. Adjacent checksums are integrity checks,
not trusted signatures. Keep artifacts in an operator-controlled directory.

`original` and `normalized` URL values are separate. URL report classifications
include `review_required`, `likely_phishing`, `likely_legitimate`; the underlying
binary decision remains visible. Rules and learned contributions are separate.
Email reports use `review_required` or `no_indicators_detected`; neither is an
independent email ML verdict. UTC timestamps describe analysis time only.

Run from the repository root so the API finds `models/`, `reports/` and
`frontend/dist/`. No compiled frontend or raw dataset is required in the Python
wheel itself. The ZIP supplies the complete repository structure.
