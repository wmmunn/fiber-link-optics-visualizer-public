from __future__ import annotations

import re


_PREFIXES = {
    "gigabitethernet": "Gi",
    "tengigabitethernet": "Te",
    "twentyfivegige": "Twe",
    "fortygigabitethernet": "Fo",
    "fiftygige": "Fi",
    "hundredgige": "Hu",
}


def normalize_interface(value: str) -> str:
    compact = re.sub(r"\s+", "", value.strip())
    lower = compact.lower()
    for long_name, short_name in _PREFIXES.items():
        if lower.startswith(long_name):
            return short_name + compact[len(long_name) :]
    aliases = (
        ("twentyfivegig", "Twe"),
        ("fortygig", "Fo"),
        ("fiftygig", "Fi"),
        ("hundredgig", "Hu"),
        ("gig", "Gi"),
        ("ten", "Te"),
    )
    for prefix, short_name in aliases:
        if lower.startswith(prefix):
            suffix = compact[len(prefix) :]
            return short_name + suffix
    match = re.match(r"(?i)^(gi|te|twe|fo|fi|hu)(.+)$", compact)
    if match:
        return match.group(1).title() + match.group(2)
    return compact
