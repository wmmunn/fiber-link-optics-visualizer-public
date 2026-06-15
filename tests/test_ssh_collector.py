import unittest
from unittest.mock import patch

from fiber_optics.ssh_collector import SshCollectorError, check_tcp_reachable


class SshCollectorTests(unittest.TestCase):
    def test_tcp_reachability_error_names_pre_auth_failure(self) -> None:
        with patch("socket.create_connection", side_effect=OSError("blocked")):
            with self.assertRaises(SshCollectorError) as context:
                check_tcp_reachable("switch.example", 22, timeout=1)

        message = str(context.exception)
        self.assertIn("switch.example:22", message)
        self.assertIn("before authentication", message)
        self.assertIn("MFA or interactive SSH", message)


if __name__ == "__main__":
    unittest.main()
