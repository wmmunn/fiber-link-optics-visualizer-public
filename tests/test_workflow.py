from pathlib import Path
import tempfile
import unittest

from fiber_optics.workflow import analyze_logs, load_endpoint_text, write_report


FIXTURES = Path(__file__).parent / "fixtures"


class WorkflowTests(unittest.TestCase):
    def test_analyzes_logs_then_exports_report(self) -> None:
        endpoint_a, endpoint_b = analyze_logs(
            a_log=FIXTURES / "endpoint_a.log",
            a_device="DIST-SW-A",
            a_interface="Te1/1/1",
            a_collected_at="2026-06-14T10:30:17-04:00",
            b_log=FIXTURES / "endpoint_b.log",
            b_device="DIST-SW-B",
            b_interface="Te1/1/1",
            b_collected_at="2026-06-14T10:30:18-04:00",
        )

        with tempfile.TemporaryDirectory() as directory:
            output = write_report(
                endpoint_a, endpoint_b, Path(directory) / "report.html"
            )
            report = output.read_text(encoding="utf-8")

        self.assertEqual(len(endpoint_a.metrics), 5)
        self.assertEqual(len(endpoint_b.metrics), 5)
        self.assertIn("1.17 dB", report)
        self.assertIn("1.35 dB", report)

    def test_loads_live_ssh_command_text(self) -> None:
        text = (FIXTURES / "endpoint_a.log").read_text(encoding="utf-8")
        endpoint = load_endpoint_text(
            "Endpoint A",
            "DIST-SW-A",
            "Te1/1/1",
            text,
            endpoint_a_collected_at(),
            "SSH: show interfaces Te1/1/1 transceiver detail",
        )

        self.assertEqual(endpoint.timestamp_source, "live SSH collection")
        self.assertEqual(endpoint.source_file, "SSH: show interfaces Te1/1/1 transceiver detail")
        self.assertEqual(len(endpoint.metrics), 5)


def endpoint_a_collected_at():
    from datetime import datetime

    return datetime.fromisoformat("2026-06-14T10:30:17-04:00")


if __name__ == "__main__":
    unittest.main()
