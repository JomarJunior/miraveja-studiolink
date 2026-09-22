"""The `miraveja-studiolink` command: run the stand-in, or check a Museum end (quickstart)."""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

import uvicorn
import yaml

from miraveja_studiolink.standin.app import create_app
from miraveja_studiolink.standin.script import apply_script
from miraveja_studiolink.standin.state import StandInState


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="miraveja-studiolink")
    subparsers = parser.add_subparsers(dest="command", required=True)

    standin = subparsers.add_parser("standin", help="Run the reference Museum end.")
    standin.add_argument("--port", type=int, default=8080)
    standin.add_argument("--host", default="127.0.0.1")
    standin.add_argument(
        "--credential",
        default=None,
        help="The Studio's bearer credential. Random if omitted (printed on startup).",
    )
    standin.add_argument(
        "--script", type=Path, default=None, help="A YAML scripting fixture to seed state from."
    )

    conformance = subparsers.add_parser(
        "conformance", help="Check any Museum end against the conformance suite."
    )
    conformance.add_argument("--target", required=True, help="Base URL of the Museum end.")
    conformance.add_argument("--credential", required=True)

    return parser


def _run_standin(args: argparse.Namespace) -> int:
    credential = args.credential or secrets.token_urlsafe(24)
    state = StandInState(credential)
    if args.script is not None:
        script_data = yaml.safe_load(args.script.read_text(encoding="utf-8")) or {}
        asyncio.run(apply_script(state, script_data))

    app = create_app(state)
    print(f"Studio Link stand-in listening on http://{args.host}:{args.port}")
    if args.credential is None:
        print(f"Generated credential (pass --credential to set your own): {credential}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _run_conformance(args: argparse.Namespace) -> int:
    from miraveja_studiolink.conformance.suite import run_suite

    report = run_suite(args.target, args.credential)
    report.print_summary()
    return 0 if report.all_passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "standin":
        return _run_standin(args)
    if args.command == "conformance":
        return _run_conformance(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
