from pathlib import Path
import tempfile
import unittest

from fiber_optics.workflow import analyze_logs, write_report


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


if __name__ == "__main__":
    unittest.main()
