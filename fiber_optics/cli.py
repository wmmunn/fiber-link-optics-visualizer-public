from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .parser import ParseError
from .workflow import generate_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a bidirectional Cisco fiber optics report from two saved CLI logs."
    )
    parser.add_argument("--a-log", required=True, type=Path, help="Endpoint A transceiver log")
    parser.add_argument("--a-device", required=True, help="Endpoint A device name")
    parser.add_argument("--a-interface", required=True, help="Endpoint A interface")
    parser.add_argument("--a-collected-at", help="Endpoint A ISO timestamp with timezone")
    parser.add_argument("--b-log", required=True, type=Path, help="Endpoint B transceiver log")
    parser.add_argument("--b-device", required=True, help="Endpoint B device name")
    parser.add_argument("--b-interface", required=True, help="Endpoint B interface")
    parser.add_argument("--b-collected-at", help="Endpoint B ISO timestamp with timezone")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("fiber_optics_report.html"),
        help="Output HTML path (default: fiber_optics_report.html)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output, _, _ = generate_report(
            a_log=args.a_log,
            a_device=args.a_device,
            a_interface=args.a_interface,
            a_collected_at=args.a_collected_at,
            b_log=args.b_log,
            b_device=args.b_device,
            b_interface=args.b_interface,
            b_collected_at=args.b_collected_at,
            output=args.output,
        )
    except (OSError, ValueError, ParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Report written to {output}")
    return 0
