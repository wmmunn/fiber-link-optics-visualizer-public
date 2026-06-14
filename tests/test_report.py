from datetime import datetime, timezone
from pathlib import Path
import unittest

from fiber_optics.analysis import build_direction
from fiber_optics.models import EndpointReading
from fiber_optics.parser import parse_cisco_transceiver
from fiber_optics.report import build_html_report


FIXTURES = Path(__file__).parent / "fixtures"


class ReportTests(unittest.TestCase):
    def test_builds_approved_three_column_report(self) -> None:
        endpoints = []
        for label, device, fixture in (
            ("Endpoint A", "DIST-SW-A", "endpoint_a.log"),
            ("Endpoint B", "DIST-SW-B", "endpoint_b.log"),
        ):
            text = (FIXTURES / fixture).read_text(encoding="utf-8")
            endpoints.append(
                EndpointReading(
                    label=label,
                    device=device,
                    interface="Te1/1/1",
                    collected_at=datetime(2026, 6, 13, 14, 32, tzinfo=timezone.utc),
                    timestamp_source="operator supplied",
                    source_file=fixture,
                    metrics=parse_cisco_transceiver(text, "Te1/1/1"),
                )
            )
        endpoint_a, endpoint_b = endpoints
        directions = (
            build_direction("A to B", endpoint_a, endpoint_b),
            build_direction("B to A", endpoint_b, endpoint_a),
        )

        report = build_html_report(endpoint_a, endpoint_b, directions)

        self.assertIn("MANUAL LOG IMPORT", report)
        self.assertIn("Actual Data Points", report)
        self.assertIn("1.17 dB", report)
        self.assertIn("1.35 dB", report)
        self.assertIn("Latest data timestamp", report)


if __name__ == "__main__":
    unittest.main()
