"""Measure an actual localhost server with synthetic inputs, without external requests."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/api-benchmark.json"))
    args = parser.parse_args()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(
        [sys.executable, "-m", "phishguard.cli", "serve", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=15, trust_env=False
        ) as client:
            for _ in range(200):
                if server.poll() is not None:
                    raise RuntimeError("Local benchmark server exited before readiness.")
                try:
                    response = client.get("/api/health")
                    response.raise_for_status()
                    assert response.json()["model_available"]
                    break
                except httpx.ConnectError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Local benchmark server did not become ready.")
            message = (ROOT / "examples/message.eml").read_bytes()
            requests = [
                (
                    "url",
                    "/api/analyze/url",
                    {"json": {"url": "https://example.org/articles/security-basics"}},
                ),
                ("email_text", "/api/analyze/email", {"json": {"content": message.decode()}}),
                (
                    "email_upload",
                    "/api/analyze/email-file",
                    {
                        "content": message,
                        "headers": {"X-Filename": "demo.eml", "Content-Type": "message/rfc822"},
                    },
                ),
            ]
            measurements = []
            for name, endpoint, payload in requests:
                durations = []
                for trial in range(33):
                    start = time.perf_counter()
                    response = client.post(endpoint, **payload)
                    elapsed = (time.perf_counter() - start) * 1000
                    response.raise_for_status()
                    assert response.json()["classification"] == "review_required"
                    if trial >= 3:
                        durations.append(elapsed)
                measurements.append(
                    {
                        "input": name,
                        "n": len(durations),
                        "warmups": 3,
                        "mean_ms": float(np.mean(durations)),
                        "median_ms": float(np.median(durations)),
                        "p95_ms": float(np.quantile(durations, 0.95)),
                    }
                )
        report = {
            "generated_utc": datetime.now(UTC).isoformat(),
            "method": "Warm sequential loopback HTTP; includes response body transfer",
            "limits": "One shared-container run; not load, cold-start or production-scale testing",
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "cpu_count": os.cpu_count(),
                "libraries": {
                    k: importlib.metadata.version(k) for k in ["fastapi", "uvicorn", "httpx"]
                },
            },
            "model_sha256": hashlib.sha256((ROOT / "models/model.json").read_bytes()).hexdigest(),
            "measurements": measurements,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(measurements, indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == "__main__":
    main()
