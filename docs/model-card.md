# Model card — char_24_C4, version 1.0.0

**Intended use:** local research and analyst support on HTTP(S) URL strings.
**Excluded use:** automatic blocking, sender authentication, incident probability,
production protection claims, or a verdict about an arbitrary webpage.

The deployed model is character TF-IDF (n-grams 2–4, maximum 30,000 terms,
case-sensitive, sublinear TF, minimum document frequency 2) with logistic
regression C=4, liblinear, maximum 400 iterations. Vocabulary/IDF/base model are
fit on the domain-disjoint training partition only. A two-parameter sigmoid is
fit on a separate calibration partition. Threshold 0.32 maximizes validation F1.
The class with score >= threshold is phishing; no hidden score inversion occurs.

Group test precision 0.999067, recall 0.992282, F1 0.995663, ROC-AUC 0.997941,
average precision 0.998231, Brier 0.003782, ECE 0.002889. These are source-specific.
The strong HTTPS/www shortcut and failure on a benign-looking example are
material limitations, not minor caveats. See error analysis before using scores.

Artifact size: 1,518,577 bytes. SHA-256:
`17d5e379f46cd3c1376d4460846ac02106ac0ded8e279a8b64d3cd1d2f7cfde8`.
Model storage contains numerical data, not executable serialization. Training
uses the attributed CC BY 4.0 dataset; no raw training corpus is bundled.

Explanations show the 12 largest TF-IDF × coefficient contributions to the raw
linear log-odds. Omitted terms and the intercept also matter. Calibration is a
separate monotone mapping; attribution is not causation. Forest code additionally
supports nonadditive single-feature replacement sensitivity using training medians.
Independent URL rules are not presented as causes of the learned prediction.

Review is required within ±0.10 of the threshold, for reserved/unknown-suffix
hosts, or at least three features outside training ranges. This is a documented
heuristic, not a validated abstention/OOD detector. Missing or invalid local model
artifacts produce rules-only API operation with no invented model score.
