"""Data-only estimator inference; never deserialize executable pickle/joblib objects."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from sklearn.feature_extraction.text import TfidfVectorizer

from phishguard.features import FEATURE_NAMES, matrix

MAX_MODEL_BYTES = 32 * 1024 * 1024


def _numeric(values, *, shape: tuple[int, ...] | None = None) -> np.ndarray:
    if np.asarray(values).dtype.kind not in "iuf":
        raise ValueError("Model numbers must have numeric types.")
    array = np.asarray(values, dtype=np.float64)
    if shape is not None and array.shape != shape:
        raise ValueError("Invalid numeric shape.")
    if not np.isfinite(array).all() or (np.abs(array) > 1e6).any():
        raise ValueError("Invalid or non-finite model number.")
    return array


class PortableModel:
    def __init__(self, data: dict):
        self.data = data
        self.spec = data["estimator"]
        self.kind = self.spec["kind"]
        self.vectorizer = None
        self.trees = []
        self._validate()
        if self.kind == "char":
            self.vectorizer = TfidfVectorizer(
                analyzer="char",
                ngram_range=tuple(self.spec["config"]["ngram_range"]),
                vocabulary=self.spec["vocabulary"],
                lowercase=False,
                sublinear_tf=True,
            )
            self.vectorizer.idf_ = np.array(self.spec["idf"])
            self.coefficients = np.array(self.spec["coefficients"])
            self.terms = self.vectorizer.get_feature_names_out()
        else:
            self.trees = [
                {k: np.asarray(v) for k, v in tree.items()} for tree in self.spec["trees"]
            ]

    def _validate(self):
        if self.data.get("schema_version") != 1 or self.kind not in {"char", "forest"}:
            raise ValueError("Unsupported model schema.")
        if not 0 < self.data["threshold"] < 1:
            raise ValueError("Invalid decision threshold.")
        _numeric([self.spec["slope"], self.spec["intercept"]], shape=(2,))
        if self.spec["slope"] <= 0:
            raise ValueError("Calibration must preserve score ordering.")
        if "feature_min" in self.data or "feature_max" in self.data:
            low = _numeric(self.data["feature_min"], shape=(len(FEATURE_NAMES),))
            high = _numeric(self.data["feature_max"], shape=(len(FEATURE_NAMES),))
            if self.data["feature_names"] != list(FEATURE_NAMES) or (low > high).any():
                raise ValueError("Invalid feature range contract.")
        if self.kind == "char":
            vocab = self.spec["vocabulary"]
            n = len(vocab)
            if (
                not 0 < n <= 30000
                or set(vocab.values()) != set(range(n))
                or any(type(v) is not int for v in vocab.values())
            ):
                raise ValueError("Invalid vocabulary.")
            low, high = self.spec["config"]["ngram_range"]
            if type(low) is not int or type(high) is not int or not 1 <= low <= high <= 5:
                raise ValueError("Invalid n-gram range.")
            if any(not low <= len(k) <= high for k in vocab):
                raise ValueError("Invalid n-gram size.")
            if (_numeric(self.spec["idf"], shape=(n,)) < 1).any():
                raise ValueError("Invalid IDF.")
            _numeric(self.spec["coefficients"], shape=(n,))
            _numeric(self.spec["bias"], shape=())
        else:
            names = self.spec["names"]
            if not names or len(set(names)) != len(names) or not set(names) <= set(FEATURE_NAMES):
                raise ValueError("Unknown feature contract.")
            if not 1 <= len(self.spec["trees"]) <= 100:
                raise ValueError("Invalid tree count.")
            _numeric(self.spec["medians"], shape=(len(names),))
            for tree in self.spec["trees"]:
                if set(tree) != {"left", "right", "feature", "threshold", "positive"}:
                    raise ValueError("Invalid tree fields.")
                n = len(tree["left"])
                if n > 32767 or n < 1 or any(len(v) != n for v in tree.values()):
                    raise ValueError("Invalid tree shape.")
                _numeric(tree["threshold"], shape=(n,))
                _numeric(tree["positive"], shape=(n,))
                depth = [0] * n
                for i, (left, right, feature) in enumerate(
                    zip(tree["left"], tree["right"], tree["feature"], strict=True)
                ):
                    if any(type(v) is not int for v in (left, right, feature)):
                        raise ValueError("Tree indices must be integers.")
                    if depth[i] > 30:
                        raise ValueError("Model tree depth exceeds limit.")
                    if left == right == -1:
                        continue
                    if not i < left < n or not i < right < n or not 0 <= feature < len(names):
                        raise ValueError("Invalid/cyclic tree.")
                    depth[left] = depth[right] = depth[i] + 1
                if not all(0 <= p <= 1 for p in tree["positive"]):
                    raise ValueError("Invalid tree probabilities.")

    def forest_probability(self, x: np.ndarray) -> np.ndarray:
        # sklearn trees compare float32 inputs, even when training arrays were float64.
        x = x.astype(np.float32)
        output = np.zeros(len(x))
        for tree in self.trees:
            nodes = np.zeros(len(x), dtype=int)
            for _ in range(32):
                active = tree["left"][nodes] != -1
                if not active.any():
                    break
                rows = np.flatnonzero(active)
                current = nodes[rows]
                go_left = x[rows, tree["feature"][current]] <= tree["threshold"][current]
                nodes[rows] = np.where(go_left, tree["left"][current], tree["right"][current])
            else:
                raise ValueError("Model tree depth exceeds limit.")
            output += tree["positive"][nodes]
        return output / len(self.trees)

    def raw(self, urls: list[str]) -> np.ndarray:
        if self.kind == "char":
            return (
                np.asarray(self.vectorizer.transform(urls) @ self.coefficients).ravel()
                + self.spec["bias"]
            )
        return logit(
            np.clip(self.forest_probability(matrix(urls, self.spec["names"])), 1e-6, 1 - 1e-6)
        )

    def predict(self, urls: list[str]) -> np.ndarray:
        return expit(self.spec["slope"] * self.raw(urls) + self.spec["intercept"])

    def explain(self, url: str) -> dict:
        if self.kind == "char":
            row = self.vectorizer.transform([url]).tocoo()
            contributions = [
                (str(self.terms[i]), float(v * self.coefficients[i]))
                for i, v in zip(row.col, row.data, strict=True)
            ]
            contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            return {
                "method": "exact linear contributions to the uncalibrated log-odds",
                "additive": True,
                "baseline": self.spec["bias"],
                "total_raw_score": float(self.raw([url])[0]),
                "items": [
                    {"feature": name, "contribution": value} for name, value in contributions[:12]
                ],
                "note": "Only the 12 largest terms are shown; omitted terms also contribute. "
                "Sigmoid calibration is a separate monotonic mapping, not causation.",
            }
        x = matrix([url], self.spec["names"])
        original = float(self.forest_probability(x)[0])
        perturbed = np.repeat(x, len(self.spec["names"]), axis=0)
        for i, median in enumerate(self.spec["medians"]):
            perturbed[i, i] = median
        delta = original - self.forest_probability(perturbed)
        indices = np.argsort(-np.abs(delta))[:10]
        return {
            "method": "single-feature replacement with training median (sensitivity)",
            "additive": False,
            "baseline": None,
            "total_raw_score": original,
            "items": [
                {"feature": self.spec["names"][i], "contribution": float(delta[i])} for i in indices
            ],
            "note": "Approximate sensitivity in uncalibrated score units. Correlated features "
            "and implausible feature combinations limit interpretation; not additive or causal.",
        }


def load_model(path: Path) -> PortableModel:
    if path.is_symlink():
        raise ValueError("Model symlinks are not accepted.")
    with path.open("rb") as file:
        raw = file.read(MAX_MODEL_BYTES + 1)
    if len(raw) > MAX_MODEL_BYTES:
        raise ValueError("Model artifact is too large.")

    def invalid_constant(_):
        raise ValueError("Non-finite model constant.")

    try:
        data = json.loads(raw, parse_constant=invalid_constant)
    except RecursionError as exc:
        raise ValueError("Model JSON nesting exceeds parser limits.") from exc
    # A local checksum detects accidental changes, not a trusted signature.
    checksum = path.with_suffix(".sha256")
    if checksum.is_symlink() or not checksum.is_file():
        raise ValueError("Model checksum missing or mismatched.")
    with checksum.open("rb") as file:
        digest = file.read(66).strip()
    if digest != hashlib.sha256(raw).hexdigest().encode():
        raise ValueError("Model checksum missing or mismatched.")
    try:
        return PortableModel(data)
    except (KeyError, TypeError, IndexError, OverflowError, AttributeError) as exc:
        raise ValueError("Invalid model structure.") from exc


def save_model(path: Path, data: dict) -> int:
    raw = json.dumps(data, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()
    if len(raw) > MAX_MODEL_BYTES:
        raise ValueError("Model artifact exceeds its serving limit.")
    path.write_bytes(raw)
    path.with_suffix(".sha256").write_text(hashlib.sha256(raw).hexdigest() + "\n")
    return len(raw)
