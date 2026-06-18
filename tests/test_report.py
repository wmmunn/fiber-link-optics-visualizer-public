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

    def test_labels_live_ssh_report(self) -> None:
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
                    timestamp_source="live SSH collection",
                    source_file=f"SSH: show interfaces Te1/1/1 transceiver detail",
                    metrics=parse_cisco_transceiver(text, "Te1/1/1"),
                )
            )
        endpoint_a, endpoint_b = endpoints
        directions = (
            build_direction("A to B", endpoint_a, endpoint_b),
            build_direction("B to A", endpoint_b, endpoint_a),
        )

        report = build_html_report(endpoint_a, endpoint_b, directions)

        self.assertIn("LIVE SSH COLLECTION", report)
        self.assertIn("live SSH", report)
        self.assertNotIn("MANUAL LOG IMPORT", report)

    def test_reports_unsupported_dom_as_limited_data(self) -> None:
        endpoint_a = EndpointReading(
            label="Endpoint A",
            device="DEMO-SW-A",
            interface="Te1/1/1",
            collected_at=datetime(2026, 6, 13, 14, 32, tzinfo=timezone.utc),
            timestamp_source="operator supplied",
            source_file="unsupported-dom.log",
            metrics=(),
        )
        text = (FIXTURES / "endpoint_b.log").read_text(encoding="utf-8")
        endpoint_b = EndpointReading(
            label="Endpoint B",
            device="DEMO-SW-B",
            interface="Te1/1/1",
            collected_at=datetime(2026, 6, 13, 14, 32, tzinfo=timezone.utc),
            timestamp_source="operator supplied",
            source_file="endpoint_b.log",
            metrics=parse_cisco_transceiver(text, "Te1/1/1"),
        )
        directions = (
            build_direction("A to B", endpoint_a, endpoint_b),
            build_direction("B to A", endpoint_b, endpoint_a),
        )

        report = build_html_report(endpoint_a, endpoint_b, directions)

        self.assertIn("Limited Data", report)
        self.assertIn("does not provide threshold-backed DOM readings", report)
        self.assertIn("Unavailable", report)


if __name__ == "__main__":
    unittest.main()
