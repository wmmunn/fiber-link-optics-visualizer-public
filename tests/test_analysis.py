from datetime import datetime, timezone
from pathlib import Path
import unittest

from fiber_optics.analysis import build_direction
from fiber_optics.models import EndpointReading
from fiber_optics.parser import parse_cisco_transceiver


FIXTURES = Path(__file__).parent / "fixtures"


def endpoint(label: str, device: str, fixture: str) -> EndpointReading:
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    return EndpointReading(
        label=label,
        device=device,
        interface="Te1/1/1",
        collected_at=datetime(2026, 6, 13, 14, 32, tzinfo=timezone.utc),
        timestamp_source="test",
        source_file=fixture,
        metrics=parse_cisco_transceiver(text, "Te1/1/1"),
    )


class AnalysisTests(unittest.TestCase):
    def test_calculates_each_direction_independently(self) -> None:
        endpoint_a = endpoint("Endpoint A", "DIST-SW-A", "endpoint_a.log")
        endpoint_b = endpoint("Endpoint B", "DIST-SW-B", "endpoint_b.log")

        a_to_b = build_direction("A to B", endpoint_a, endpoint_b)
        b_to_a = build_direction("B to A", endpoint_b, endpoint_a)

        self.assertAlmostEqual(a_to_b.loss_db or 0, 1.17)
        self.assertAlmostEqual(b_to_a.loss_db or 0, 1.35)
        self.assertEqual(a_to_b.status, "ok")
        self.assertEqual(b_to_a.status, "ok")


if __name__ == "__main__":
    unittest.main()
