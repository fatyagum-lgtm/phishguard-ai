"""Run the entire experimental path on synthetic fixtures; no performance claim."""

import argparse
from pathlib import Path

from phishguard.research.plots import generate
from phishguard.research.preprocess import clean_rows
from phishguard.research.runner import run_frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output directory.")
    rows = []
    for domain in range(160):
        for page in range(2):
            label = domain % 2
            url = (
                f"http://verify-{domain}.example.test/login/secure?page={page}"
                if label
                else f"https://docs-{domain}.example.test/guide/{page}"
            )
            rows.append((url, label))
    frame, cleaning = clean_rows(rows)
    cleaning["synthetic"] = True
    report = run_frame(frame, cleaning, args.output, smoke=True)
    generate(report, args.output / "figures")
    assert report["dataset"]["archive_sha256"] is None
    assert all(m.get("export_max_error", 0) < 1e-10 for m in report["models"])
    print("Synthetic pipeline smoke passed; these scores are not research benchmarks.")


if __name__ == "__main__":
    main()
