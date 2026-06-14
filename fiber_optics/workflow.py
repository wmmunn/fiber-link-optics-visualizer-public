from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .analysis import build_direction
from .interfaces import normalize_interface
from .models import EndpointReading
from .parser import parse_cisco_transceiver
from .report import build_html_report


def parse_timestamp(value: str | None, source: Path) -> tuple[datetime, str]:
    if value and value.strip():
        cleaned = value.strip()
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError as exc:
            raise ValueError(
                f"Invalid timestamp {cleaned!r}; use ISO format such as "
                "2026-06-14T10:30:18-04:00."
            ) from exc
        if parsed.tzinfo is None:
            raise ValueError(f"Timestamp {cleaned!r} must include a UTC offset.")
        return parsed, "operator supplied"
    return datetime.fromtimestamp(source.stat().st_mtime).astimezone(), "log file modified time"


def load_endpoint(
    label: str,
    device: str,
    interface: str,
    log_path: Path,
    collected_at: str | None,
) -> EndpointReading:
    if not device.strip():
        raise ValueError(f"{label} device name is required.")
    if not interface.strip():
        raise ValueError(f"{label} interface is required.")
    if not log_path.is_file():
        raise ValueError(f"{label} log file does not exist: {log_path}")

    timestamp, timestamp_source = parse_timestamp(collected_at, log_path)
    text = log_path.read_text(encoding="utf-8-sig", errors="replace")
    metrics = parse_cisco_transceiver(text, interface)
    return EndpointReading(
        label=label,
        device=device.strip(),
        interface=normalize_interface(interface),
        collected_at=timestamp,
        timestamp_source=timestamp_source,
        source_file=log_path.name,
        metrics=metrics,
    )


def analyze_logs(
    *,
    a_log: Path,
    a_device: str,
    a_interface: str,
    a_collected_at: str | None,
    b_log: Path,
    b_device: str,
    b_interface: str,
    b_collected_at: str | None,
) -> tuple[EndpointReading, EndpointReading]:
    endpoint_a = load_endpoint(
        "Endpoint A", a_device, a_interface, a_log, a_collected_at
    )
    endpoint_b = load_endpoint(
        "Endpoint B", b_device, b_interface, b_log, b_collected_at
    )
    return endpoint_a, endpoint_b


def write_report(
    endpoint_a: EndpointReading,
    endpoint_b: EndpointReading,
    output: Path,
) -> Path:
    directions = (
        build_direction("A to B", endpoint_a, endpoint_b),
        build_direction("B to A", endpoint_b, endpoint_a),
    )
    report = build_html_report(endpoint_a, endpoint_b, directions)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return output.resolve()


def generate_report(
    *,
    a_log: Path,
    a_device: str,
    a_interface: str,
    a_collected_at: str | None,
    b_log: Path,
    b_device: str,
    b_interface: str,
    b_collected_at: str | None,
    output: Path,
) -> tuple[Path, EndpointReading, EndpointReading]:
    endpoint_a, endpoint_b = analyze_logs(
        a_log=a_log,
        a_device=a_device,
        a_interface=a_interface,
        a_collected_at=a_collected_at,
        b_log=b_log,
        b_device=b_device,
        b_interface=b_interface,
        b_collected_at=b_collected_at,
    )
    resolved = write_report(endpoint_a, endpoint_b, output)
    return resolved, endpoint_a, endpoint_b
