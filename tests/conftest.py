from pathlib import Path

import pytest

from phishguard.model import load_model
from phishguard.research.preprocess import clean_rows

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def model():
    return load_model(ROOT / "models/model.json")


@pytest.fixture
def sample_frame():
    rows = []
    for i in range(160):
        label = i % 2
        for page in range(2):
            url = (
                f"http://verify-{i}.example.test/login/secure?page={page}"
                if label
                else f"https://docs-{i}.example.test/guide/{page}"
            )
            rows.append((url, label))
    return clean_rows(rows)[0]
