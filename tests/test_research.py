import copy
import json
from itertools import combinations

import numpy as np
import pytest

from phishguard.features import FEATURE_NAMES
from phishguard.model import PortableModel, load_model, save_model
from phishguard.research.learners import Learner
from phishguard.research.metrics import bootstrap_f1, evaluate, select_threshold
from phishguard.research.preprocess import clean_rows, make_splits, sample_rows
from phishguard.research.robustness import synthetic_urls, transform


def test_duplicates_conflicting_labels_and_missing():
    frame, info = clean_rows(
        [
            ("https://EXAMPLE.org", 0),
            ("https://example.org/", 0),
            ("https://conflict.test", 0),
            ("https://conflict.test", 1),
            ("http://verify.example.test", 1),
            ("", 0),
        ]
    )
    assert len(frame) == 2
    assert info["duplicate_rows_removed"] == 1
    assert info["conflicting_label_rows_removed"] == 2
    assert info["invalid_rows"] == 1


@pytest.mark.parametrize("protocol", ["random", "domain_disjoint"])
def test_split_reproducibility_and_leakage(sample_frame, protocol):
    a, details = make_splits(sample_frame, protocol, 2026)
    b, _ = make_splits(sample_frame, protocol, 2026)
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert sorted(np.concatenate(list(a.values()))) == list(range(len(sample_frame)))
    for x, y in combinations(a, 2):
        assert not set(a[x]) & set(a[y])
        if protocol == "domain_disjoint":
            assert not set(sample_frame.domain.iloc[a[x]]) & set(sample_frame.domain.iloc[a[y]])
    assert all(v["exact_urls"] == 0 for v in details["overlaps"])
    assert sample_rows(sample_frame, 100, 2026).equals(sample_rows(sample_frame, 100, 2026))


@pytest.mark.parametrize("kind", ["char", "forest"])
def test_fitted_export_calibration_and_reproducibility(sample_frame, tmp_path, kind):
    split, _ = make_splits(sample_frame, "domain_disjoint", 2026)
    urls = {k: sample_frame.url.iloc[v].tolist() for k, v in split.items()}
    y = {k: sample_frame.label.iloc[v].to_numpy() for k, v in split.items()}
    config = {"ngram_range": [2, 4], "C": 1.0}
    names = list(FEATURE_NAMES) if kind == "forest" else []
    learner = Learner("test", kind, config, names).fit(urls["train"], y["train"], 2026, True)
    before = learner.export()
    learner.calibrate(urls["calibration"], y["calibration"])
    after = learner.export()
    before.pop("slope")
    before.pop("intercept")
    check = copy.deepcopy(after)
    check.pop("slope")
    check.pop("intercept")
    assert before == check  # Calibration must not refit the base estimator.
    data = {"schema_version": 1, "threshold": 0.5, "estimator": after}
    path = tmp_path / "model.json"
    save_model(path, data)
    loaded = load_model(path)
    np.testing.assert_allclose(
        loaded.predict(urls["test"]), learner.predict(urls["test"]), atol=1e-12
    )
    assert loaded.predict(urls["test"]).shape == (len(urls["test"]),)
    assert loaded.explain(urls["test"][0])["items"]
    again = Learner("test", kind, config, names).fit(urls["train"], y["train"], 2026, True)
    np.testing.assert_allclose(again.raw(urls["test"]), learner.raw(urls["test"]), atol=1e-12)
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="checksum"):
        load_model(path)


def test_metrics_and_cluster_bootstrap():
    y, p = np.array([0, 0, 1, 1]), np.array([0.1, 0.8, 0.4, 0.9])
    metric = evaluate(y, p, 0.5)
    assert metric["confusion_matrix"] == [[1, 1], [1, 1]]
    assert metric["precision"] == metric["recall"] == metric["f1"] == 0.5
    assert evaluate(np.array([0, 0]), np.array([0.1, 0.2]), 0.5)["roc_auc"] is None
    assert evaluate(y, p, 0.5, probability=False)["brier"] is None
    assert 0.1 <= select_threshold(y, p) <= 0.9
    a = bootstrap_f1(y, p, ["a", "a", "b", "b"], 0.5, 2026)
    assert a == bootstrap_f1(y, p, ["a", "a", "b", "b"], 0.5, 2026)
    assert 0 <= a["low"] <= a["high"] <= 1


def test_model_missing_and_invalid_shapes(model):
    from phishguard.service import analyze_url

    result = analyze_url("https://example.org", None)
    assert result["classification"] == "review_required" and result["score"] is None
    data = copy.deepcopy(model.data)
    data["estimator"]["coefficients"] = []
    with pytest.raises(ValueError, match="shape"):
        PortableModel(data)


def test_canonical_perturbations_are_stable(model):
    from phishguard.urls import parse_url

    values = synthetic_urls()
    for category in ["host_case", "unreserved_encoding"]:
        changed = [parse_url(transform(u, category)).normalized for u in values]
        original = [parse_url(u).normalized for u in values]
        assert original == changed
        np.testing.assert_array_equal(model.predict(changed), model.predict(original))


def test_real_report_leakage_and_artifacts():
    from conftest import ROOT

    report = json.loads((ROOT / "reports/research.json").read_text())
    assert report["dataset"]["sample_rows"] == 40000
    assert all(
        x["domains"] == 0 and x["exact_urls"] == 0
        for x in report["protocols"]["domain_disjoint"]["overlaps"]
    )
    assert all(m.get("export_max_error", 0) < 1e-10 for m in report["models"])


@pytest.mark.parametrize("rows", [[], [("invalid", 0)], [("https://example.org", 1)]])
def test_cleaning_without_two_classes_is_explicit(rows):
    with pytest.raises(ValueError, match="both classes"):
        clean_rows(rows)


@pytest.mark.parametrize(
    "field,value",
    [("slope", float("inf")), ("intercept", 1e300), ("bias", float("nan")), ("slope", -1)],
)
def test_model_rejects_nonfinite_or_invalid_numeric_artifacts(model, field, value):
    data = copy.deepcopy(model.data)
    data["estimator"][field] = value
    with pytest.raises(ValueError):
        PortableModel(data)


def test_host_case_preserves_userinfo_case():
    from phishguard.urls import parse_url

    original = "https://User:Secret@ExAmple.org/Test"
    assert parse_url(original).normalized == parse_url(transform(original, "host_case")).normalized


def test_bias_diagnostic_is_descriptive_and_training_only(sample_frame):
    from phishguard.research.diagnostics import collection_bias

    diagnostic = collection_bias(sample_frame.iloc[:50])
    assert sum(row["rows"] for row in diagnostic["by_label"]) == 50
    assert diagnostic["used_for_model_selection"] is False
