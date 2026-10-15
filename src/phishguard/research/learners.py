"""Small, inspectable sklearn training wrappers with disjoint sigmoid calibration."""

import time
from dataclasses import dataclass

import numpy as np
from scipy.special import expit, logit
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from phishguard.features import FEATURE_NAMES, matrix


@dataclass
class Learner:
    name: str
    kind: str
    config: dict
    names: list[str]
    vectorizer: TfidfVectorizer | None = None
    estimator: object | None = None
    slope: float = 1.0
    intercept: float = 0.0
    training_seconds: float = 0.0
    medians: list[float] | None = None

    def fit(self, urls: list[str], y: np.ndarray, seed: int, smoke=False):
        start = time.perf_counter()
        if self.kind == "char":
            self.vectorizer = TfidfVectorizer(
                analyzer="char",
                ngram_range=tuple(self.config["ngram_range"]),
                max_features=30000,
                min_df=2,
                lowercase=False,
                sublinear_tf=True,
                dtype=np.float64,
            )
            x = self.vectorizer.fit_transform(urls)
            self.estimator = LogisticRegression(
                C=self.config["C"], solver="liblinear", max_iter=400, random_state=seed
            )
        else:
            x = matrix(urls, self.names)
            self.medians = np.median(x, axis=0).tolist()
            self.estimator = RandomForestClassifier(
                n_estimators=24 if smoke else 100,
                max_depth=14,
                min_samples_leaf=3,
                max_features=0.8,
                random_state=seed,
                n_jobs=2,
            )
        self.estimator.fit(x, y)
        self.training_seconds = time.perf_counter() - start
        return self

    def raw(self, urls: list[str]) -> np.ndarray:
        if self.kind == "char":
            return self.estimator.decision_function(self.vectorizer.transform(urls))
        return logit(
            np.clip(self.estimator.predict_proba(matrix(urls, self.names))[:, 1], 1e-6, 1 - 1e-6)
        )

    def calibrate(self, urls: list[str], y: np.ndarray):
        # A regularized two-parameter sigmoid, fitted ONLY on the calibration split.
        calibration = LogisticRegression(C=1000, solver="lbfgs", max_iter=200)
        calibration.fit(self.raw(urls).reshape(-1, 1), y)
        self.slope = float(calibration.coef_[0, 0])
        self.intercept = float(calibration.intercept_[0])
        if self.slope <= 0:
            raise ValueError("Calibration reversed score ordering; investigate the experiment.")
        return self

    def predict(self, urls: list[str], calibrated=True) -> np.ndarray:
        raw = self.raw(urls)
        return expit(self.slope * raw + self.intercept) if calibrated else expit(raw)

    def export(self) -> dict:
        base = {
            "name": self.name,
            "kind": self.kind,
            "config": self.config,
            "slope": self.slope,
            "intercept": self.intercept,
            "names": self.names,
        }
        if self.kind == "char":
            base.update(
                {
                    "vocabulary": {k: int(v) for k, v in self.vectorizer.vocabulary_.items()},
                    "idf": self.vectorizer.idf_.tolist(),
                    "coefficients": self.estimator.coef_[0].tolist(),
                    "bias": float(self.estimator.intercept_[0]),
                }
            )
        else:
            trees = []
            for estimator in self.estimator.estimators_:
                tree = estimator.tree_
                values = tree.value[:, 0, :]
                trees.append(
                    {
                        "left": tree.children_left.tolist(),
                        "right": tree.children_right.tolist(),
                        "feature": tree.feature.tolist(),
                        "threshold": tree.threshold.tolist(),
                        "positive": (values[:, 1] / values.sum(axis=1)).tolist(),
                    }
                )
            base.update(
                {
                    "trees": trees,
                    "medians": self.medians,
                    "importance": self.estimator.feature_importances_.tolist(),
                }
            )
        return base


def candidates(smoke=False) -> list[Learner]:
    configs = (
        [((3, 5), 1.0)] if smoke else [((3, 5), 1.0), ((3, 5), 4.0), ((2, 4), 1.0), ((2, 4), 4.0)]
    )
    return [
        Learner(f"char_{a}{b}_C{c:g}", "char", {"ngram_range": [a, b], "C": c}, [])
        for (a, b), c in configs
    ] + [Learner("lexical_forest", "forest", {"family": "all"}, list(FEATURE_NAMES))]
