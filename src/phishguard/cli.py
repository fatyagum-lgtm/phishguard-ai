"""Explicit offline workflows; only the acquire command accesses a public dataset URL."""

import argparse
import json
from pathlib import Path

from phishguard import __version__


def main():
    parser = argparse.ArgumentParser(
        description="PhishGuard AI — local phishing research and investigation"
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    acquire = commands.add_parser(
        "acquire", help="Download the fixed public UCI dataset, not its sample URLs"
    )
    acquire.add_argument("--output", type=Path, default=Path("data/raw/phiusiil.zip"))
    train = commands.add_parser(
        "research", help="Clean, partition, train and evaluate the verified UCI dataset"
    )
    train.add_argument("--archive", type=Path, default=Path("data/raw/phiusiil.zip"))
    train.add_argument("--output", type=Path, required=True)
    train.add_argument("--samples", type=int, default=40000)
    train.add_argument("--seed", type=int, default=2026)
    train.add_argument(
        "--smoke", action="store_true", help="Reduced model search, not the full experiment"
    )
    server = commands.add_parser(
        "serve", help="Serve the local API and built frontend at 127.0.0.1:8000"
    )
    server.add_argument("--port", type=int, default=8000)
    server.add_argument("--model", type=Path, default=Path("models/model.json"))
    for name in ("url", "email"):
        command = commands.add_parser(name, help=f"Analyze a {name} offline and print JSON")
        command.add_argument("input", type=Path if name == "email" else str)
        command.add_argument("--model", type=Path, default=Path("models/model.json"))
    args = parser.parse_args()
    try:
        if args.command == "acquire":
            from phishguard.research.data import acquire as download

            print(json.dumps({"sha256": download(args.output), "file": args.output.name}))
        elif args.command == "research":
            from phishguard.research.plots import generate
            from phishguard.research.runner import run

            report = run(args.archive, args.output, args.samples, args.seed, args.smoke)
            generate(report, args.output / "figures")
        elif args.command == "serve":
            import uvicorn

            from phishguard.api import create_app

            uvicorn.run(
                create_app(model_path=args.model),
                host="127.0.0.1",
                port=args.port,
                access_log=False,
                limit_concurrency=16,
            )
        else:
            from phishguard.email_analysis import MAX_EMAIL_BYTES
            from phishguard.model import load_model
            from phishguard.service import analyze_email, analyze_url

            model = load_model(args.model) if args.model.exists() else None
            if args.command == "url":
                result = analyze_url(args.input, model)
            else:
                with args.input.open("rb") as file:
                    result = analyze_email(file.read(MAX_EMAIL_BYTES + 1), model)
            print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
    except (ValueError, OSError) as exc:
        # InputError texts never echo private content; OS errors use only class, not filename.
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        parser.exit(2, f"Error: {message}\n")


if __name__ == "__main__":
    main()
