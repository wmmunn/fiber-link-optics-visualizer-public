import unittest
from unittest.mock import patch

from fiber_optics.ssh_collector import (
    SshCollectorError,
    build_transceiver_command,
    check_tcp_reachable,
    validate_device_type,
)


class SshCollectorTests(unittest.TestCase):
    def test_tcp_reachability_error_names_pre_auth_failure(self) -> None:
        with patch("socket.create_connection", side_effect=OSError("blocked")):
            with self.assertRaises(SshCollectorError) as context:
                check_tcp_reachable("switch.example", 22, timeout=1)

        message = str(context.exception)
        self.assertIn("switch.example:22", message)
        self.assertIn("before authentication", message)
        self.assertIn("MFA or interactive SSH", message)

    def test_rejects_unsupported_device_type(self) -> None:
        with self.assertRaises(SshCollectorError):
            validate_device_type("linux")

    def test_accepts_supported_device_type(self) -> None:
        self.assertEqual(validate_device_type("cisco_ios"), "cisco_ios")

    def test_builds_catalyst_transceiver_command(self) -> None:
        self.assertEqual(
            build_transceiver_command("cisco_ios", "Te1/1/1"),
            "show interfaces Te1/1/1 transceiver detail",
        )

    def test_builds_nexus_transceiver_command(self) -> None:
        self.assertEqual(
            build_transceiver_command("cisco_nxos", "Eth3/31"),
            "show int Eth3/31 transceiver details",
        )


if __name__ == "__main__":
    unittest.main()
