from __future__ import annotations

from dataclasses import dataclass
import socket


class SshCollectorError(RuntimeError):
    """Raised when live SSH collection cannot proceed."""


ALLOWED_DEVICE_TYPES = {"cisco_ios", "cisco_xe", "cisco_nxos"}


def netmiko_available() -> bool:
    try:
        import netmiko  # noqa: F401
    except ImportError:
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


def validate_device_type(device_type: str) -> str:
    cleaned = device_type.strip() or "cisco_ios"
    if cleaned not in ALLOWED_DEVICE_TYPES:
        supported = ", ".join(sorted(ALLOWED_DEVICE_TYPES))
        raise SshCollectorError(
            f"Unsupported Netmiko device type {cleaned!r}. Supported values: {supported}."
        )
    return cleaned


def detect_device_type_from_show_version(output: str) -> str | None:
    text = (output or "").lower()
    if "nx-os" in text or "nexus" in text or "cisco nexus operating system" in text:
        return "cisco_nxos"
    if "ios xe" in text or "ios-xe" in text or "cisco ios xe software" in text:
        return "cisco_xe"
    if "cisco ios software" in text or "ios software" in text:
        return "cisco_ios"
    return None


def build_transceiver_command(device_type: str, interface: str) -> str:
    normalized_device_type = validate_device_type(device_type)
    if normalized_device_type == "cisco_nxos":
        return f"show int {interface} transceiver details"
    return f"show interfaces {interface} transceiver detail"


@dataclass
class CiscoSshSession:
    host: str
    username: str
    port: int = 22
    device_type: str = "cisco_ios"
    strict_host_key: bool = False
    timeout: int = 45

    def __post_init__(self) -> None:
        self.device_type = validate_device_type(self.device_type)
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
                ssh_strict=self.strict_host_key,
                system_host_keys=self.strict_host_key,
            )
        except Exception as exc:
            raise SshCollectorError(f"SSH login failed for {self.host}: {exc}") from exc

    def detect_device_type(self) -> str | None:
        output = self.command("show version")
        detected = detect_device_type_from_show_version(output)
        if detected:
            self.device_type = detected
        return detected

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
