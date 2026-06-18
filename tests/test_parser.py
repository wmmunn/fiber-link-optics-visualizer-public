from pathlib import Path
import unittest

from fiber_optics.interfaces import normalize_interface
from fiber_optics.parser import (
    ParseError,
    discover_interfaces,
    dom_readings_unavailable,
    parse_cisco_transceiver,
)


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
        self.assertEqual(normalize_interface("Ethernet3/31"), "Eth3/31")
        self.assertEqual(normalize_interface("eth1/49"), "Eth1/49")

    def test_discovers_twenty_five_gigabit_interface_from_realistic_table(self) -> None:
        text = """
                         High Alarm  High Warn  Low Warn  Low Alarm
             Temperature Threshold   Threshold  Threshold Threshold
Port         (Celsius)   (Celsius)   (Celsius)  (Celsius) (Celsius)
Twe1/0/22   43.4        89.0        85.0       -5.0      -9.0
"""

        self.assertEqual(discover_interfaces(text), ("Twe1/0/22",))

    def test_parses_nexus_sfp_detail_diagnostics(self) -> None:
        text = """
         SFP Detail Diagnostics Information (internal calibration)
  ----------------------------------------------------------------------------
                Current              Alarms                  Warnings
                Measurement     High        Low         High          Low
  ----------------------------------------------------------------------------
  Temperature   25.43 C        90.00 C    -10.00 C     85.00 C       -5.00 C
  Voltage        3.32 V         3.63 V      2.97 V      3.47 V        3.14 V
  Current       16.17 mA       65.09 mA     2.40 mA    61.00 mA       3.00 mA
  Tx Power      -6.96 dBm       0.00 dBm  -13.00 dBm   -2.99 dBm     -9.50 dBm
  Rx Power      -6.66 dBm       0.00 dBm  -23.01 dBm   -2.99 dBm    -19.03 dBm
  Transmit Fault Count = 0
  ----------------------------------------------------------------------------
"""

        readings = parse_cisco_transceiver(text, "Eth1/49")
        by_metric = {reading.metric: reading for reading in readings}

        self.assertEqual(len(readings), 5)
        self.assertEqual(by_metric["Temperature"].value, 25.43)
        self.assertEqual(by_metric["Voltage"].low_warn, 3.14)
        self.assertEqual(by_metric["Current"].high_alarm, 65.09)
        self.assertEqual(by_metric["Tx Power"].low_alarm, -13.00)
        self.assertEqual(by_metric["Rx Power"].high_warn, -2.99)

    def test_returns_empty_readings_when_dom_is_not_supported(self) -> None:
        text = """
Te1/1/1
  Transceiver monitoring is not supported on this module.
  Digital optical monitoring: not available
"""

        readings = parse_cisco_transceiver(text, "Te1/1/1")

        self.assertEqual(readings, ())
        self.assertTrue(dom_readings_unavailable(text))


if __name__ == "__main__":
    unittest.main()
