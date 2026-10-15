# Validation record

The machine-readable result is `reports/validation/summary.json`; each command's
actual stdout/stderr is retained beside it. `python scripts/validate.py` creates
these records; it fails on a nonzero command result and does not fabricate passes.

## Scope and environment

Validated locally on Linux x86-64, Python 3.12.14 and Node 24.19.0 (npm 11.9.0).
A fresh isolated virtual environment was installed from `pyproject.toml`, then
its resolved versions were recorded in `requirements-lock.txt`. React/Node
packages are project-local and locked by `frontend/package-lock.json`.
Dependencies were installed under the user's explicit authorization.

Two real 40,000-row UCI studies completed, with full train/calibration/validation/test
separation, two ablations, export-equivalence checks and controlled perturbations.
`reports/reproduction-check.json` records identical dataset/split membership,
selected model bytes and decision metrics. A strict 1e-10 aggregate comparison
failed because forest rank metrics differ by 1.18e-7; the documented 1e-6 comparison
passes. This is disclosed, not represented as bitwise forest reproducibility.

## Final outcome

**All 11 local validation command groups passed.** Python: **68 passed**, with
one documented deprecation warning. Frontend: **4 passed**. Browser: **1 passed**.
The final record is timestamped in UTC in the machine-readable summary.

## Executed checks

| Command | What it validates |
|---|---|
| `python -m pytest -q` | 68 URL, email, dataset, model, calibration, split and API cases |
| `ruff check src tests scripts` | Python lint and basic static checks |
| `ruff format --check src tests scripts` | Python formatting |
| `python -m pip check` | Installed Python dependency compatibility |
| `npm run format:check --prefix frontend` | Prettier source/config formatting |
| `npm run test --prefix frontend` | 4 React tests: navigation, validation, errors, safe strings |
| `npm run build --prefix frontend` | Strict TypeScript checking and Vite production build |
| `npm run e2e --prefix frontend` | Real API/browser workflow, uploads, charts, downloads, mobile layout |
| `python scripts/smoke_research.py --output NEW_DIRECTORY` | Entire training/export/plot path on 320 synthetic rows |
| `python scripts/demo.py` | Actual URL/email reports using the included real-data model |
| `python scripts/benchmark_api.py` | Warm loopback URL/text/upload latency, 30 requests each |
| `npm audit --json` | Zero reported advisories at execution; saved in `reports/npm-audit.json` |

The browser test compares displayed model scores and dataset counts against actual
HTTP API responses, injects hostile HTML strings without execution, uploads `.eml`,
switches protocols/models, exports JSON and checks 390px layouts. It records zero
external browser requests and no page errors for the exercised flows. These are
specific tested observations, not a guarantee for every possible input.
Screenshots in `docs/screenshots/` are captured directly by this test.

## Failures investigated and corrected

- An initial scientific-library combination crashed in native SciPy import.
  The tested numerical stack is pinned to NumPy 2.3.5 / SciPy 1.17.0 / sklearn 1.8.0.
- API CSP literal construction, alternate numeric host parsing and ambiguous
  bracket/port syntax were corrected and regression-tested.
- TypeScript Node declarations were added for browser configuration; a frontend
  matcher misuse was corrected. Neither failure was silently skipped.
- Playwright 1.51 was upgraded to 1.56.1 after an audit advisory. Browser downloads
  from the first official CDN were invalid; the installer succeeded through its
  standard official fallback. After workspace suspension its browser cache was
  missing; it was restored and the integration check rerun.
- Long-line lint failures in documentation/benchmark scripts were corrected.
- An accidental workspace-wide pytest invocation collected unrelated projects and
  failed import collection. All reported project tests use the PhishGuard root;
  unrelated project source was not changed.

One Starlette TestClient deprecation warning remains: its current release prefers
httpx2 while the tested httpx adapter still works. No warning was suppressed.
Environment-provided npm proxy/terminal warnings are recorded in logs.

## Limits of validation

GitHub Actions is configured but has **not run on GitHub**. There is no published
repository or fabricated CI badge. No coverage percentage, formal penetration
test, production-scale throughput, Windows/macOS compatibility, external-dataset
accuracy or authenticated email identity is claimed. The UI has visual checks and
keyboard-friendly semantics, but no formal accessibility certification.

## Archive extraction check

The release ZIP was extracted into a new directory. Fresh `npm ci`, the production
build, CLI help, synthetic reports and the real browser/API workflow all passed
there. Python used the existing isolated dependency environment and the extracted
`src/` via PYTHONPATH. See `reports/validation/archive-check.json`. No global Node
packages or raw dataset were required to run the included trained model.
