"""Execute the local acceptance checks and retain their real outputs."""

import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    destination = ROOT / "reports/validation"
    destination.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    results = []
    with tempfile.TemporaryDirectory(prefix="phishguard-smoke-") as temporary:
        commands = [
            (
                "python-lint",
                [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
                ROOT,
            ),
            (
                "python-format",
                [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts"],
                ROOT,
            ),
            ("python-tests", [sys.executable, "-m", "pytest", "-q"], ROOT),
            ("python-dependencies", [sys.executable, "-m", "pip", "check"], ROOT),
            ("frontend-format", ["npm", "run", "format:check"], ROOT / "frontend"),
            ("frontend-tests", ["npm", "run", "test"], ROOT / "frontend"),
            ("frontend-build", ["npm", "run", "build"], ROOT / "frontend"),
            ("browser-integration", ["npm", "run", "e2e"], ROOT / "frontend"),
            (
                "research-smoke",
                [
                    sys.executable,
                    "scripts/smoke_research.py",
                    "--output",
                    str(Path(temporary) / "run"),
                ],
                ROOT,
            ),
            ("cli-help", [sys.executable, "-m", "phishguard.cli", "--help"], ROOT),
            ("synthetic-demo", [sys.executable, "scripts/demo.py"], ROOT),
        ]
        for name, command, directory in commands:
            print(f"Checking {name}...", flush=True)
            result = subprocess.run(
                command, cwd=directory, env=environment, capture_output=True, text=True, timeout=300
            )
            output = (
                (result.stdout + result.stderr)
                .replace(str(ROOT), "<project>")
                .replace(sys.prefix, "<venv>")
                .replace(temporary, "<temporary>")
            )
            (destination / (name + ".txt")).write_text(output)
            shown = [
                "python" if part == sys.executable else part.replace(temporary, "<temporary>")
                for part in command
            ]
            results.append(
                {
                    "name": name,
                    "command": shown,
                    "directory": str(directory.relative_to(ROOT)),
                    "exit_code": result.returncode,
                }
            )
            print(f"{name}: exit {result.returncode}", flush=True)
            if result.returncode:
                print(output)
                break
    report = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "all_passed": len(results) == len(commands) and all(r["exit_code"] == 0 for r in results),
        "checks": results,
        "hosted_ci_run": False,
    }
    (destination / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
