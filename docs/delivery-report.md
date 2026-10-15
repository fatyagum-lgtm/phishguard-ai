# Delivery report

## A. Completion status

All seven implementation stages are complete for the documented **local research
release**. All 18 acceptance criteria in the supplied brief are addressed by the
implemented application, real experiments and executed checks. Production or
external-domain validity is not implied. The final local validation has 11 passing
command groups; detailed evidence is retained in `reports/validation/`.

## B. Implemented functionality

Offline URL normalization, lexical features, trained inference, model-specific
explanations, uncertainty/review flags and JSON export; bounded text/raw/EML email
inspection with URL inference, independent indicators and unverified header claims;
a real five-screen research dashboard with interactive protocols/models and charts.

## C. Architecture

Python `src/phishguard/`: shared URL contract, MIME parser, data-only model loader,
report services, typed FastAPI boundary and argparse CLI. `research/`: source
acquisition, deduplication, split manifests, training, calibration, evaluation and
plots. React/TypeScript is compiled by Vite and served by FastAPI on loopback.
No cloud inference, paid API, database of private messages or executable pickle.
See architecture.md and threat-model.md.

## D. Dataset provenance

UCI PhiUSIIL 967, Prasad & Chandra (2024), CC BY 4.0. SHA-verified archive, raw URL
and label only. 235,795 raw → 234,885 clean → 40,000 sampled rows. Internal phishing
label is 1, explicitly inverted from original UCI 0. No dataset URL was visited.
See dataset-card.md for exact fingerprints, exclusions and collection bias.

## E. Actual ML results

| Domain-disjoint model | Precision | Recall | F1 | Brier |
|---|---:|---:|---:|---:|
| Selected character LR | 0.999067 | 0.992282 | 0.995663 | 0.003782 |
| Lexical forest | 0.991895 | 0.982402 | 0.987126 | 0.008417 |
| Forest without host family | 0.986415 | 0.919111 | 0.951574 | 0.030303 |
| Forest without HTTPS | 0.917548 | 0.910466 | 0.913993 | 0.059470 |
| Fixed rules | 1.000000 | 0.012349 | 0.024398 | — |

Selection was by validation F1 with lower Brier/FPR tie breakers. Calibration had
its own partition; final test was evaluated afterward. The selected model has
7,879 test cases, threshold 0.32 and matrix `[[4637,3],[25,3214]]`.
Random-split character F1 is 0.995580: no material group penalty was observed.
These strong source-specific values coexist with substantial formatting bias and
safe synthetic failure cases. See results.md and technical-report.md.

## F. Robustness research

Seven measured categories: casing, unreserved encoding, query/path changes,
subdomain depth, and exploratory scheme/www changes. Canonical checks use 400
real holdout URLs; other pairs use 60 reserved-domain synthetic inputs. Learned
binary decisions stayed stable, often at saturated incorrect-looking scores;
this is not proof of robustness. Two controlled forest ablations also ran.
See robustness-study.md and the actual paired examples in reports/research.json.

## G. Validation

68 Python tests; 4 React tests; 1 real browser workflow; Ruff lint/format;
Prettier; TypeScript/Vite production build; pip dependency checks; synthetic
pipeline smoke; real demos; two real-data experiments; actual loopback API timing.
One TestClient deprecation warning remains, documented and unsuppressed.
All final local check commands passed. npm audit reported zero advisories at
execution. `docs/validation.md` lists commands, corrected failures and scope.

## H. UI and launch

Follow README Quick start to create an isolated Python environment, install the
locked dependencies, install project-local Node packages and build the client.
`python -m phishguard.cli serve` then serves **http://127.0.0.1:8000**.
Five genuine browser captures are in `docs/screenshots/`; scientific plots are
in `reports/figures/`. These are actual application and experiment outputs.

## I. Known limitations

Strong HTTPS/www source association, one subset/seed/source, no temporal or
external evaluation, limited near-duplicate analysis, no trained email model,
no independent SPF/DKIM/DMARC verification and no attachment scanning. Local
single-user deployment only. Linux was tested; macOS/Windows, Docker, hosted CI
and production load were not. Small forest ranking drift is disclosed.

## J. Publication

No Git commit, remote repository or push was created. Publication commands are
in publication.md for the user's later decision. The configured workflow must
actually run on GitHub before claiming hosted CI success.

## K. Future research

Independent timestamped data; campaign-aware separation; multiple seeds;
format-bias mitigation; explicit false-positive/miss costs; separately labeled
email evaluation. These are motivated next steps, not advertised current features.
