"""Explicit public-data acquisition and label handling, independent of inference."""

import csv
import hashlib
import io
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

SOURCE = "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip"
EXPECTED_SHA256 = "0a639fd03aea6308c5b1c10c92aa23c2ce1505447a9137271865cd0badc9a59a"
MEMBER = "PhiUSIIL_Phishing_URL_Dataset.csv"
MAX_ARCHIVE = 20 * 1024 * 1024
MAX_CSV = 80 * 1024 * 1024


def map_label(value: str) -> int:
    """UCI 1=legitimate, 0=phishing; internal positive class 1=phishing."""
    if value not in {"0", "1"}:
        raise ValueError("Unexpected UCI label; expected exactly 0 or 1.")
    return 1 - int(value)


def acquire(destination: Path) -> str:
    """Download only the fixed official dataset; never visit its URL samples."""
    if destination.exists():
        raise FileExistsError("Dataset destination already exists.")
    with urllib.request.urlopen(SOURCE, timeout=90) as response:
        data = response.read(MAX_ARCHIVE + 1)
    if len(data) > MAX_ARCHIVE:
        raise ValueError("Dataset archive exceeds the configured size limit.")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Dataset hash changed. Review provenance before accepting new bytes.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as file:
        file.write(data)
    return digest


def read_archive(path: Path, *, verify: bool = True) -> list[tuple[str, int]]:
    """Read only URL and label; no ZIP extraction or website-derived features."""
    with path.open("rb") as file:
        data = file.read(MAX_ARCHIVE + 1)
    if len(data) > MAX_ARCHIVE:
        raise ValueError("Dataset archive exceeds the configured size limit.")
    if verify and hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Dataset archive checksum mismatch.")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != MEMBER:
            raise ValueError("Unexpected dataset archive members.")
        if members[0].file_size > MAX_CSV:
            raise ValueError("Uncompressed dataset exceeds the configured size limit.")
        with archive.open(MEMBER) as stream:
            rows = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
            if not rows.fieldnames or not {"URL", "label"}.issubset(rows.fieldnames):
                raise ValueError("Expected URL and label columns.")
            return [(row["URL"], map_label(row["label"])) for row in rows]


def describe(rows: list[tuple[str, int]]) -> dict:
    labels = Counter(label for _, label in rows)
    return {
        "rows": len(rows),
        "legitimate": labels[0],
        "phishing": labels[1],
        "missing_url": sum(not url for url, _ in rows),
        "internal_labels": {"0": "legitimate", "1": "phishing"},
    }
