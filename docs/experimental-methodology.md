# Experimental methodology

Seed **2026**. Normalize scheme/host, IDNA hostnames, default ports and unreserved
percent escapes; preserve path/query/fragment case. Retain original values
separately. Reject ambiguous numeric hosts, invalid authorities, unsupported
schemes and malformed encodings. Remove exact normalized duplicates before any
partitioning; discard every conflicting-label group. Sort by normalized URL SHA.
Select 40,000 rows using a stratified seeded subset, then sort again by identifier.

Four partitions prevent reuse of calibration data as threshold-selection data.
The random protocol uses stratified row splits. The group protocol uses successive
`GroupShuffleSplit` calls on registrable domains (bundled PSL, private suffixes
included; unknown suffixes fall back to full hostname). Seeds are 2026, 2027, 2028.
Hold out 20% of groups for test, 12.5% of the remainder for calibration, then 1/7
of the remainder for validation. Group fractions are not exact row fractions.

| Protocol | Train | Calibration | Validation | Test |
|---|---:|---:|---:|---:|
| Random | 24,000 | 4,000 | 4,000 | 8,000 |
| Domain-disjoint | 24,117 | 3,925 | 4,079 | 7,879 |

Every partition must contain both classes. All six pairwise exact overlaps are
zero. Group protocol also has zero domain/template overlap. Random train/test
shares 348 domains and 233 templates. Templates are a limited diagnostic, not a
comprehensive campaign split. Model artifacts are fit solely on training data.

Character grid: n-grams (3,5)/(2,4), C 1/4, maximum 30,000 terms, min_df=2,
sublinear TF, no lowercase conversion. Forest: 100 trees, depth 14, minimum leaf
3, max_features=0.8, two workers. BLAS is limited to one thread during experiments.
Sigmoid calibration fits LogisticRegression(C=1000, lbfgs) to base margins
(or clipped RF probability logits) on calibration only. This is a regularized
two-parameter sigmoid, not sklearn's exact Platt target-smoothing implementation.
Slope must be positive. Threshold grid 0.10–0.90 in steps of 0.01 maximizes
validation F1, preferring the nearest 0.5 on ties. Model selection maximizes
validation F1, breaking ties with lower Brier then lower FPR. The selected model
is not refit on combined partitions; final test is used after choices are fixed.

Ablations retrain the same forest/calibration protocol without nine host-family
features or without HTTPS, then select their thresholds on validation. Correlated
proxy features remain, so ablations are not causal removal of all host/scheme
information. Fixed rules use three weighted points (index >=0.5); this conservative
baseline was not tuned after test inspection and is not a strong tuned comparator.

Report precision, recall, F1, FPR/FNR, ROC-AUC, average precision (not trapezoidal
PR area), Brier and 10-bin equal-width ECE. Metrics use complete predictions;
plotted PR/ROC curves are downsampled to at most 101 points. F1 intervals resample
whole domain clusters 200 times and condition on one fit and split. They do not
cover dataset choice, retraining, seed or labeling uncertainty. Tiny calibration
bins can be very noisy despite low aggregate ECE.

HTTPS/www class-frequency diagnostics and the last two synthetic perturbations
were added **after** initial result inspection, explicitly as exploratory work;
no model, hyperparameter or threshold was retuned using them. Two real runs have
identical sample/split manifests, selected model bytes and decision metrics.
All metric differences are <=1.18e-7; a strict 1e-10 comparison failed on forest
ranking metrics. A 1e-6 comparison with exact decision checks is recorded, not
bitwise forest reproducibility. Export equivalence within each run remains 1e-10.

Sources: [sklearn calibration](https://scikit-learn.org/1.8/modules/calibration.html),
[GroupShuffleSplit](https://scikit-learn.org/1.8/modules/generated/sklearn.model_selection.GroupShuffleSplit.html),
[tldextract](https://github.com/john-kurkowski/tldextract). Reproduction commands are
in README. `--smoke --samples 1000` reduces real-data search; `scripts/smoke_research.py`
uses 320 synthetic rows and never establishes detection performance.
