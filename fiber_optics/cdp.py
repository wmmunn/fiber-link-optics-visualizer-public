from __future__ import annotations

from dataclasses import dataclass
import re

from .interfaces import normalize_interface


@dataclass(frozen=True)
class CdpNeighbor:
    device_id: str
    local_interface: str
    remote_interface: str


def _device_matches(candidate: str, expected: str) -> bool:
    if not expected.strip():
        return True
    left = candidate.strip().lower().split(".", 1)[0]
    right = expected.strip().lower().split(".", 1)[0]
    return left == right or right in candidate.strip().lower()


def parse_cdp_neighbors_detail(text: str) -> tuple[CdpNeighbor, ...]:
    neighbors: list[CdpNeighbor] = []
    device_id = ""
    local_interface = ""
    remote_interface = ""

    def flush() -> None:
        nonlocal device_id, local_interface, remote_interface
        if device_id and local_interface and remote_interface:
            neighbors.append(
                CdpNeighbor(
                    device_id=device_id.strip(),
                    local_interface=normalize_interface(local_interface),
                    remote_interface=normalize_interface(remote_interface),
                )
            )
        device_id = ""
        local_interface = ""
        remote_interface = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("device id:"):
            flush()
            device_id = line.split(":", 1)[1].strip()
            continue
        match = re.search(
            r"(?i)^interface:\s*(.+?),\s*port id\s*\(outgoing port\):\s*(.+)$",
            line,
        )
        if match:
            local_interface = match.group(1).strip()
            remote_interface = match.group(2).strip()

    flush()
    return tuple(neighbors)


def find_cdp_link(
    text: str,
    local_interface: str,
    expected_remote_device: str = "",
) -> CdpNeighbor:
    target = normalize_interface(local_interface)
    matches = [
        neighbor
        for neighbor in parse_cdp_neighbors_detail(text)
        if neighbor.local_interface.lower() == target.lower()
        and _device_matches(neighbor.device_id, expected_remote_device)
    ]
    if not matches:
        expected_note = (
            f" and remote device matching {expected_remote_device!r}"
            if expected_remote_device.strip()
            else ""
        )
        raise ValueError(
            f"No CDP neighbor found for local interface {target}{expected_note}."
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple CDP neighbors matched {target}; refine the expected B-side device."
        )
    return matches[0]
