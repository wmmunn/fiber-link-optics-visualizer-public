from pathlib import Path
import unittest

from fiber_optics.interfaces import normalize_interface
from fiber_optics.parser import ParseError, discover_interfaces, parse_cisco_transceiver


FIXTURES = Path(__file__).parent / "fixtures"


class ParserTests(unittest.TestCase):
    def test_parses_compact_cisco_threshold_tables(self) -> None:
        text = (FIXTURES / "endpoint_a.log").read_text(encoding="utf-8")

        readings = parse_cisco_transceiver(text, "TenGigabitEthernet1/1/1")
        by_metric = {reading.metric: reading for reading in readings}

        self.assertEqual(len(readings), 5)
        self.assertEqual(by_metric["Temperature"].value, 38.30)
        self.assertEqual(by_metric["Tx Power"].low_warn, -8.50)
        self.assertEqual(by_metric["Rx Power"].value, -7.02)
        self.assertEqual(by_metric["Rx Power"].level, "ok")

    def test_rejects_unknown_interface(self) -> None:
        text = (FIXTURES / "endpoint_a.log").read_text(encoding="utf-8")

        with self.assertRaises(ParseError):
            parse_cisco_transceiver(text, "Te1/1/9")

    def test_normalizes_common_cisco_names(self) -> None:
        self.assertEqual(normalize_interface("TenGigabitEthernet1/1/1"), "Te1/1/1")
        self.assertEqual(normalize_interface("te1/1/1"), "Te1/1/1")
        self.assertEqual(normalize_interface("GigabitEthernet1/0/48"), "Gi1/0/48")

    def test_discovers_twenty_five_gigabit_interface_from_realistic_table(self) -> None:
        text = """
                         High Alarm  High Warn  Low Warn  Low Alarm
             Temperature Threshold   Threshold  Threshold Threshold
Port         (Celsius)   (Celsius)   (Celsius)  (Celsius) (Celsius)
Twe1/0/22   43.4        89.0        85.0       -5.0      -9.0
"""

        self.assertEqual(discover_interfaces(text), ("Twe1/0/22",))


if __name__ == "__main__":
    unittest.main()
