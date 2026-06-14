from __future__ import annotations

import re

from .interfaces import normalize_interface
from .models import MetricReading


METRIC_ORDER = ("Temperature", "Voltage", "Current", "Tx Power", "Rx Power")
METRIC_UNITS = {
    "Temperature": "C",
    "Voltage": "V",
    "Current": "mA",
    "Tx Power": "dBm",
    "Rx Power": "dBm",
}


class ParseError(ValueError):
    """Raised when selected-interface transceiver data cannot be parsed."""


def discover_interfaces(text: str) -> tuple[str, ...]:
    interfaces: set[str] = set()
    for raw_line in text.splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 2:
            continue
        interface = normalize_interface(parts[0])
        if not re.match(r"(?i)^(gi|te|twe|fo|fi|hu)\d", interface):
            continue
        numeric_count = 0
        for token in parts[1:]:
            try:
                float(token)
                numeric_count += 1
            except ValueError:
                continue
        if numeric_count:
            interfaces.add(interface)
    return tuple(sorted(interfaces))


def _metric_from_text(line: str) -> str:
    lower = line.lower()
    if "temperature" in lower:
        return "Temperature"
    if "voltage" in lower:
        return "Voltage"
    if "current" in lower or "laser bias" in lower:
        return "Current"
    if "transmit" in lower or "tx power" in lower:
        return "Tx Power"
    if "receive" in lower or "rx power" in lower:
        return "Rx Power"
    return ""


def _numbers(text: str) -> list[float]:
    return [float(value) for value in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text)]


def _reading(metric: str, numeric: list[float]) -> MetricReading:
    value, high_alarm, high_warn, low_warn, low_alarm = numeric[:5]
    return MetricReading(
        metric=metric,
        unit=METRIC_UNITS[metric],
        value=value,
        low_alarm=low_alarm,
        low_warn=low_warn,
        high_warn=high_warn,
        high_alarm=high_alarm,
    )


def _parse_compact_rows(text: str, target: str) -> dict[str, MetricReading]:
    readings: dict[str, MetricReading] = {}
    pending_metric = ""
    inferred_index = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        header_metric = _metric_from_text(line)
        if header_metric and not re.match(r"(?i)^(gi|te|twe|fo|fi|hu)", line):
            pending_metric = header_metric
            continue

        parts = line.split()
        if len(parts) < 6 or normalize_interface(parts[0]).lower() != target.lower():
            continue
        numeric = []
        for token in parts[1:]:
            try:
                numeric.append(float(token))
            except ValueError:
                continue
        if len(numeric) < 5:
            continue
        metric = pending_metric
        if not metric and inferred_index < len(METRIC_ORDER):
            metric = METRIC_ORDER[inferred_index]
        if metric in METRIC_UNITS:
            readings[metric] = _reading(metric, numeric)
            inferred_index += 1
            pending_metric = ""
    return readings


def _parse_verbose_rows(text: str, target: str) -> dict[str, MetricReading]:
    readings: dict[str, MetricReading] = {}
    current_interface = ""
    values: dict[str, float] = {}
    thresholds: dict[str, tuple[float, float, float, float]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        interface_header = normalize_interface(line.rstrip(":"))
        if line.endswith(":") and re.match(r"(?i)^(gi|te|twe|fo|fi|hu)\d", interface_header):
            current_interface = interface_header
            continue
        if current_interface and current_interface.lower() != target.lower():
            continue

        match = re.match(
            r"(?i)^(?:optical\s+)?"
            r"(temperature|voltage|current|laser\s+bias\s+current|tx\s+power|rx\s+power|"
            r"transmit\s+power|receive\s+power)\s+(value|threshold)\s+(.+)$",
            line,
        )
        if not match:
            continue
        metric = _metric_from_text(match.group(1))
        numeric = _numbers(match.group(3))
        if match.group(2).lower() == "value" and numeric:
            values[metric] = numeric[0]
        elif match.group(2).lower() == "threshold" and len(numeric) >= 4:
            thresholds[metric] = (numeric[0], numeric[1], numeric[2], numeric[3])

    for metric, value in values.items():
        if metric not in thresholds:
            continue
        high_alarm, high_warn, low_warn, low_alarm = thresholds[metric]
        readings[metric] = MetricReading(
            metric=metric,
            unit=METRIC_UNITS[metric],
            value=value,
            low_alarm=low_alarm,
            low_warn=low_warn,
            high_warn=high_warn,
            high_alarm=high_alarm,
        )
    return readings


def parse_cisco_transceiver(text: str, interface: str) -> tuple[MetricReading, ...]:
    target = normalize_interface(interface)
    readings = _parse_compact_rows(text, target)
    readings.update(_parse_verbose_rows(text, target))
    ordered = tuple(readings[name] for name in METRIC_ORDER if name in readings)
    if not ordered:
        detected = discover_interfaces(text)
        detected_note = (
            f" Detected interface(s): {', '.join(detected)}."
            if detected
            else " No transceiver interfaces were detected."
        )
        raise ParseError(
            f"No threshold-backed transceiver readings were parsed for interface {interface!r}. "
            f"Confirm the interface name and include the detailed Cisco transceiver output."
            f"{detected_note}"
        )
    return ordered
