# Offline Phishing URL Detection under Domain Separation and Controlled Perturbations

PhishGuard AI · independent research implementation · October 2026

## Abstract

We evaluate offline URL-only phishing detectors on a seeded 40,000-row subset of
UCI PhiUSIIL. Character TF-IDF logistic regression, a 26-feature random forest and
fixed lexical rules are compared using random and domain-disjoint four-way splits.
Calibration and validation selection use separate partitions. The selected character
model achieves group-test F1 0.995663 and Brier 0.003782. However, all legitimate
group-training URLs contain HTTPS and www, and a benign-looking reserved-domain
example receives a phishing estimate of 0.999226. Thus, high within-source metrics
coexist with severe transfer concerns. A local URL/email application exposes
these limitations, real experimental artifacts and model-specific explanations.

## 1. Introduction

Offline URL strings offer a low-cost way to prioritize investigation without
contacting a suspicious host. They cannot establish the intent or content of a
page. Evaluation may reward collection artifacts that are stable across domain
names. This study investigates that gap and makes its failure modes inspectable.
It is an independent reconstruction and extension inspired by an earlier team-led
ShellHacks 2026 prototype; no original code or historical experiments are claimed.

## 2. Research questions

1. How do character and engineered lexical models compare under random versus
   registrable-domain-disjoint evaluation?
2. How do held-out calibration and removal of feature families change results?
3. Which controlled transformations affect scores, decisions and rule findings?
4. How can email observations augment URL inference without misrepresenting
   unverified authentication headers or inventing an email classifier?

## 3. Data and methods

PhiUSIIL [1] contains 235,795 rows. Only raw URL and label are used. Source 0 denotes
phishing; this implementation explicitly maps it to internal 1. Strict parsing,
normalization, deduplication and complete removal of contradictory-label groups
leave 234,885 rows. The 40,000-row stratified subset contains 17,036 phishing labels
and 35,641 registrable-domain groups. Source labels are not independently verified.

Character TF-IDF uses up to 30,000 terms, sublinear counts and case preservation.
A four-configuration n-gram/regularization grid is selected on validation. The
forest uses 100 trees with depth 14 and minimum leaf size 3. Fixed rules combine
userinfo, IP host, HTTP, length, depth and keyword observations; their conservative
three-point threshold is not tuned on test. Two-parameter sigmoid calibration is
fit on an independent calibration partition [2]. No website features or online
lookups enter inference. Full details appear in experimental-methodology.md.

## 4. Experimental setup

Seed 2026 controls sampling and partitioning. Random splits are stratified by label.
GroupShuffleSplit [3] separates registrable domains, including private suffixes
from an offline bundled PSL [4]. Four group partitions contain 24,117 training,
3,925 calibration, 4,079 validation and 7,879 test rows. All six pairwise exact and
domain overlaps are zero. In the random protocol, 348 domains overlap train/test.

Thresholds maximize validation F1 on a declared grid; validation F1 also chooses
the deployment model. Final test evaluation occurs afterward. Ablations remove
nine host features or HTTPS from the forest and repeat the same procedure.
Domain-cluster bootstrap intervals use 200 resamples and condition on the fitted
model. Models are exported to bounded data-only JSON and compared with sklearn
on every test input. The API and browser tests exercise real local inference.

## 5. Results

| Model | Random F1 | Domain-disjoint F1 | Group Brier |
|---|---:|---:|---:|
| Character LR | 0.995580 | 0.995663 | 0.003782 |
| Lexical forest | 0.986086 | 0.987126 | 0.008417 |
| Fixed rules | 0.016303 | 0.024398 | Not a probability |
| Forest without host family | — | 0.951574 | 0.030303 |
| Forest without HTTPS | — | 0.913993 | 0.059470 |

The selected character configuration is n-grams 2–4, C=4, threshold 0.32.
Group-test precision is 0.999067 and recall 0.992282, with 3 false positives and
25 false negatives. Conditional cluster-bootstrap F1 interval is 0.994125–0.997310.
Calibration reduces character Brier from 0.005122 to 0.003782 and ECE from 0.0151
to 0.002889. It does not improve every model: the no-host forest's Brier worsens.

There is no material random-to-group F1 drop. This does not establish universal
generalization: every legitimate training URL uses HTTPS and www. The corresponding
phishing fractions are 50.17% and 40.01%. Removing HTTPS lowers forest F1 by 0.073132,
consistent with a strong source-specific association. Correlated proxy features
remain, so this is not a causal effect estimate. The fixed rule baseline has poor
recall and should not be presented as a competitive industrial reference.

## 6. Robustness analysis

Five planned categories cover host casing, unreserved encoding, query addition,
path extension and synthetic subdomain depth. Two exploratory diagnostics add
scheme switching and www prefixing. Canonical checks use 400 real holdout strings;
other categories use 60 reserved-domain synthetic strings with no assumed labels.
No sample is visited. Canonicalization makes the first two checks invariant by
design. Learned-model decisions do not flip in the synthetic suite; initial
scores are often saturated, including docs-like strings. This stability is not
proof of adversarial robustness. Prefixing www changes character scores by
0.025965 on average, while half of rule decisions flip under added host depth.
See robustness-study.md for the complete measured table and scope of review rates.

## 7. Error analysis

Several high-confidence false negatives have HTTPS/www formatting. Character
coefficients strongly favor those markers toward legitimate labels. Conversely,
a harmless-looking synthetic URL without www receives 0.999226. The application
retains this result and requires review, exposing poor transfer rather than
curating only favorable examples. The error-analysis document includes defanged
held-out errors and distinguishes inherited labels from verified website intent.

Email inspection combines these URL scores with deterministic observations.
The fixture's forged Authentication-Results claims remain unverified. Keyword
rules flag even benign advice mentioning a password, so they are observations,
not semantic understanding. No labeled email experiment or email accuracy is claimed.

## 8. Limitations and threats to validity

One source, subset and seed limit inference. Group separation does not guarantee
campaign separation. Collection-time generalization is untested, near-duplicate
checks are limited, and labels may be outdated or incorrect. Calibration is
conditional on source distribution; small reliability bins are noisy. Bootstrap
intervals omit retraining and source uncertainty. Synthetic perturbations may
change semantics and do not establish real-world evasion.

Two real runs reproduced split membership and selected model bytes exactly;
forest ranking metrics drifted by up to 1.18e-7. A strict 1e-10 metric comparison
failed, while exact decision metrics and the documented 1e-6 comparison passed.
Physical hardware allocation was not established; measured timings describe a
shared Linux container. No hosted CI, remote deployment, formal security audit
or production-load validation is claimed. Scope is local, single-user research.

## 9. Conclusion

Offline URL models perform strongly within this source, even with domain-disjoint
splits, but formatting shortcuts substantially weaken interpretation. The most
important finding is the coexistence of excellent holdout metrics and clear
synthetic transfer failures. Independent, timestamped and less format-biased
validation is the next requirement before operational claims. The delivered
application makes the evidence, uncertainty and reproducibility path inspectable.

## References

1. Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website),
   [UCI dataset 967](https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset).
   Associated publication: [10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545).
2. Scikit-learn 1.8. [Probability calibration](https://scikit-learn.org/1.8/modules/calibration.html).
3. Scikit-learn 1.8. [GroupShuffleSplit](https://scikit-learn.org/1.8/modules/generated/sklearn.model_selection.GroupShuffleSplit.html).
4. Tldextract. [Official documentation and source](https://github.com/john-kurkowski/tldextract).
5. Python. [email.parser](https://docs.python.org/3/library/email.parser.html).
6. OWASP. [File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
