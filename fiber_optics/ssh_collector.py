from __future__ import annotations

from dataclasses import dataclass
import socket


class SshCollectorError(RuntimeError):
    """Raised when live SSH collection cannot proceed."""


def netmiko_available() -> bool:
    try:
        import netmiko  # noqa: F401
    except Exception:
        return False
    return True


def check_tcp_reachable(host: str, port: int, timeout: int = 8) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return
    except OSError as exc:
        raise SshCollectorError(
            f"TCP connection to {host}:{port} failed before authentication.\n\n"
            "MFA or interactive SSH prompts will not appear until the SSH server is reachable.\n\n"
            "Check the hostname/IP, SSH port, VPN/jump-host requirements, and firewall policy."
        ) from exc


@dataclass
class CiscoSshSession:
    host: str
    username: str
    port: int = 22
    device_type: str = "cisco_ios"
    timeout: int = 45

    def __post_init__(self) -> None:
        self._connection = None

    @property
    def connected(self) -> bool:
        return self._connection is not None

    def connect(self, password: str) -> None:
        try:
            from netmiko import ConnectHandler
        except Exception as exc:
            raise SshCollectorError(
                "Netmiko is not installed. Install it with: python -m pip install netmiko"
            ) from exc

        try:
            check_tcp_reachable(self.host, self.port)
            self._connection = ConnectHandler(
                device_type=self.device_type,
                host=self.host,
                port=self.port,
                username=self.username,
                password=password,
                auth_timeout=self.timeout,
                banner_timeout=self.timeout,
                conn_timeout=self.timeout,
            )
        except Exception as exc:
            raise SshCollectorError(f"SSH login failed for {self.host}: {exc}") from exc

    def command(self, command: str) -> str:
        if self._connection is None:
            raise SshCollectorError(f"Not connected to {self.host}.")
        try:
            return self._connection.send_command(command, read_timeout=self.timeout)
        except Exception as exc:
            raise SshCollectorError(
                f"Command failed on {self.host}: {command}: {exc}"
            ) from exc

    def disconnect(self) -> None:
        if self._connection is None:
            return
        try:
            self._connection.disconnect()
        finally:
            self._connection = None
