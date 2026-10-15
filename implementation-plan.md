# Implementation plan

This is a new independent implementation. Existing projects in the workspace
are outside its scope.

1. Inspect the official UCI PhiUSIIL source, verify labels and license, acquire
   the archive without following any sample URL, and fingerprint the bytes.
2. Build one strict offline URL parser and feature contract shared by training
   and serving. Use tldextract's bundled PSL with all fetching disabled.
3. Deduplicate normalized URLs and discard all conflicting-label groups. Run
   seeded random and registrable-domain-disjoint train/calibration/validation/test
   partitions. Train on train only; fit sigmoid calibration on calibration only;
   select hyperparameters, thresholds and deployment model on validation only.
4. Compare fixed rules, character TF-IDF logistic regression and a lexical random
   forest. Add structural-family and scheme ablations, calibration comparison,
   grouped bootstrap intervals and controlled offline perturbations. Never use
   website-derived UCI columns.
5. Export the selected estimator to data-only JSON, with prediction-equivalence
   checks against the fitted sklearn estimator; no pickle loading in the server.
6. Add bounded MIME/HTML parsing, explicit unverified authentication claims,
   hybrid email observations, typed FastAPI routes and same-origin local serving.
7. Build React/TypeScript investigation and research screens from real API data.
8. Execute Python, API, frontend, end-to-end and reproducibility checks. Record
   measured results, limitations, screenshots and a clean installation workflow.

Primary scope is local single-user use. No URL retrieval, DNS lookup, active
email HTML, attachment execution, cloud inference or private-message persistence.
Network access is used only for explicit setup and dataset acquisition.

The initial research run uses a seeded, documented subset for laptop-sized
experiments; it is not a replication of the dataset authors' website-feature
model. The untouched final test is evaluated after validation-based choices.
