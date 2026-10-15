"""Produce real investigation reports for safe, explicitly synthetic examples."""

import argparse
import json
from pathlib import Path

from phishguard.model import load_model
from phishguard.service import analyze_email, analyze_url

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/demo"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    model = load_model(ROOT / "models/model.json")
    reports = {
        "url-benign-looking": analyze_url("https://example.org/articles/security-basics", model),
        "url-with-www": analyze_url("https://www.example.org/articles/security-basics", model),
        "url-suspicious-pattern": analyze_url(
            "http://account-verify.example.test/login/secure?user=demo", model
        ),
        "email": analyze_email((ROOT / "examples/message.eml").read_bytes(), model),
    }
    for name, report in reports.items():
        (args.output / (name + ".json")).write_text(
            json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        )
        print(f"{name}: {report['classification']}; model estimate={report.get('score')}")
    print("These fixtures exercise behavior; they do not validate real-world detection.")


if __name__ == "__main__":
    main()
