from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import webbrowser

try:
    import ttkbootstrap as tb

    TTKBOOTSTRAP_AVAILABLE = True
except Exception:
    tb = None
    TTKBOOTSTRAP_AVAILABLE = False

from .analysis import build_direction
from .cdp import find_cdp_link
from .models import DirectionReading, EndpointReading, MetricReading
from .interfaces import normalize_interface
from .parser import ParseError, discover_interfaces
from .ssh_collector import (
    CiscoSshSession,
    SshCollectorError,
    build_transceiver_command,
    netmiko_available,
    validate_device_type,
)
from .workflow import analyze_logs, load_endpoint_text, read_log_text, write_report


APP_NAME = "Fiber Link Optics Visualizer"
APP_VERSION = "0.3.5"
APP_AUTHOR = "Created by William Munn"
SSH_DEVICE_TYPES = ("cisco_ios", "cisco_xe", "cisco_nxos")


class App(tb.Window if TTKBOOTSTRAP_AVAILABLE else tk.Tk):
    def __init__(self) -> None:
        if TTKBOOTSTRAP_AVAILABLE:
            super().__init__(themename="flatly")
        else:
            super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1220x800")
        self.minsize(980, 680)

        self.a_log = tk.StringVar()
        self.a_device = tk.StringVar()
        self.a_interface = tk.StringVar(value="Te1/1/1")
        self.a_timestamp = tk.StringVar()
        self.b_log = tk.StringVar()
        self.b_device = tk.StringVar()
        self.b_interface = tk.StringVar(value="Te1/1/1")
        self.b_timestamp = tk.StringVar()
        self.ssh_username = tk.StringVar()
        self.ssh_port = tk.StringVar(value="22")
        self.ssh_device_type = tk.StringVar(value="cisco_ios")
        self.strict_host_key = tk.BooleanVar(value=False)
        self.ssh_status = tk.StringVar(
            value="Live SSH is optional. Manual log import remains available. Strict host key verification is off unless you enable it."
        )
        self.summary_text = tk.StringVar(
            value="Load two transceiver logs and run analysis."
        )

        self.a_session: CiscoSshSession | None = None
        self.b_session: CiscoSshSession | None = None
        self.endpoint_a: EndpointReading | None = None
        self.endpoint_b: EndpointReading | None = None
        self.directions: tuple[DirectionReading, DirectionReading] | None = None
        self.last_report: Path | None = None
        self.result_details: list[str] = []

        self._build_ui()

    def _button(self, parent, text: str, command, bootstyle: str = ""):
        if TTKBOOTSTRAP_AVAILABLE:
            return tb.Button(
                parent,
                text=text,
                command=command,
                bootstyle=bootstyle or "secondary",
            )
        return ttk.Button(parent, text=text, command=command)

    def _build_ui(self) -> None:
        if TTKBOOTSTRAP_AVAILABLE:
            self.style.configure(
                "Tool.TLabelframe.Label", font=("Segoe UI", 10, "bold")
            )

        top = ttk.Frame(self, padding=14)
        top.pack(fill="x")

        header = ttk.Frame(top)
        header.grid(row=0, column=0, sticky="we", pady=(0, 12))
        ttk.Label(header, text=APP_NAME, font=("Segoe UI", 17, "bold")).pack(
            side="left"
        )
        ttk.Label(
            header,
            text=f"v{APP_VERSION}",
            font=("Segoe UI", 10),
            foreground="#5c6b73",
        ).pack(side="left", padx=(8, 0), pady=(6, 0))
        ttk.Label(
            header,
            text="Manual import or operator-gated read-only SSH; no credential storage.",
            foreground="#5c6b73",
        ).pack(side="right", pady=(6, 0))
        input_frame = ttk.LabelFrame(
            top,
            text="Inputs",
            padding=10,
            style="Tool.TLabelframe" if TTKBOOTSTRAP_AVAILABLE else "",
        )
        input_frame.grid(row=1, column=0, sticky="we")
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(4, weight=1)

        self._endpoint_inputs(
            input_frame,
            0,
            "Endpoint A",
            self.a_log,
            self.a_device,
            self.a_interface,
            self.a_timestamp,
        )
        ttk.Separator(input_frame, orient="vertical").grid(
            row=0, column=3, rowspan=5, sticky="ns", padx=14
        )
        self._endpoint_inputs(
            input_frame,
            4,
            "Endpoint B",
            self.b_log,
            self.b_device,
            self.b_interface,
            self.b_timestamp,
        )
        ttk.Label(
            input_frame,
            text=(
                "Timestamp is optional. Leave blank to use the log file modification "
                "time, clearly labeled in the report."
            ),
            foreground="#5c6b73",
        ).grid(row=5, column=0, columnspan=7, sticky="w", pady=(8, 0))

        ssh_frame = ttk.LabelFrame(
            top,
            text="Live SSH Collection (Optional, Read-Only)",
            padding=10,
            style="Tool.TLabelframe" if TTKBOOTSTRAP_AVAILABLE else "",
        )
        ssh_frame.grid(row=2, column=0, sticky="we", pady=(10, 0))
        ssh_frame.columnconfigure(1, weight=1)
        ssh_frame.columnconfigure(4, weight=1)
        ssh_frame.columnconfigure(7, weight=1)
        ttk.Label(ssh_frame, text="Username").grid(row=0, column=0, sticky="w")
        ttk.Entry(ssh_frame, textvariable=self.ssh_username, width=28).grid(
            row=0, column=1, sticky="w", padx=(8, 18)
        )
        ttk.Label(ssh_frame, text="SSH port").grid(row=0, column=2, sticky="w")
        ttk.Entry(ssh_frame, textvariable=self.ssh_port, width=7).grid(
            row=0, column=3, sticky="w", padx=(8, 18)
        )
        self._button(
            ssh_frame, "Connect A", lambda: self.connect_live_endpoint("A"), "primary"
        ).grid(row=0, column=4, padx=4)
        self._button(
            ssh_frame, "Discover B via CDP", self.discover_b_from_a, "primary-outline"
        ).grid(row=0, column=5, padx=4)
        self._button(
            ssh_frame, "Collect A Optics", lambda: self.collect_live_endpoint("A"), "success"
        ).grid(row=0, column=6, padx=4)
        ttk.Label(ssh_frame, text="Device type").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Combobox(
            ssh_frame,
            textvariable=self.ssh_device_type,
            values=SSH_DEVICE_TYPES,
            state="readonly",
            width=14,
        ).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Checkbutton(
            ssh_frame,
            text="Strict host key verification",
            variable=self.strict_host_key,
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=(8, 0), padx=(0, 18))
        self._button(
            ssh_frame, "Connect B", lambda: self.connect_live_endpoint("B"), "primary"
        ).grid(row=1, column=4, padx=4, pady=(8, 0))
        self._button(
            ssh_frame, "Collect B Optics", lambda: self.collect_live_endpoint("B"), "success"
        ).grid(row=1, column=5, padx=4, pady=(8, 0))
        self._button(
            ssh_frame, "Build Live Report", self.build_live_report, "success-outline"
        ).grid(row=1, column=6, padx=4, pady=(8, 0))
        ttk.Label(
            ssh_frame,
            textvariable=self.ssh_status,
            foreground="#5c6b73",
            wraplength=1120,
        ).grid(row=2, column=0, columnspan=7, sticky="w", pady=(8, 0))
        top.columnconfigure(0, weight=1)

        buttons = ttk.Frame(self, padding=(14, 0, 14, 10))
        buttons.pack(fill="x")
        self._button(
            buttons, "Analyze Logs", self.run_analysis, "success"
        ).pack(side="left", padx=(0, 6))
        self.export_button = self._button(
            buttons, "Export HTML", self.export_html, "primary-outline"
        )
        self.export_button.pack(side="left", padx=6)
        self.open_button = self._button(
            buttons, "Open Last Report", self.open_report, "primary-outline"
        )
        self.open_button.pack(side="left", padx=6)
        self._button(buttons, "Clear", self.clear, "secondary-outline").pack(
            side="left", padx=6
        )
        self._button(buttons, "Exit", self.destroy, "secondary-outline").pack(
            side="right"
        )
        ttk.Label(
            buttons,
            text=APP_AUTHOR,
            foreground="#5c6b73",
            font=("Segoe UI", 9),
        ).pack(side="right", padx=(0, 14), pady=(6, 0))

        self.summary = ttk.Label(
            self,
            textvariable=self.summary_text,
            padding=(14, 2, 14, 10),
            font=("Segoe UI", 11, "bold"),
        )
        self.summary.pack(fill="x")

        columns = ("status", "scope", "metric", "detail")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for column, width in (
            ("status", 90),
            ("scope", 170),
            ("metric", 180),
            ("detail", 720),
        ):
            self.tree.heading(column, text=column.title())
            self.tree.column(column, width=width, anchor="w")
        self.tree.tag_configure(
            "ALARM", foreground="#9b0000", background="#fff1f0"
        )
        self.tree.tag_configure(
            "WARN", foreground="#7a4d00", background="#fff8e6"
        )
        self.tree.tag_configure(
            "PASS", foreground="#176b1d", background="#eef8ef"
        )
        self.tree.tag_configure(
            "INFO", foreground="#34454d", background="#f5f7f8"
        )
        self.tree.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self.show_detail)

        detail_frame = ttk.LabelFrame(
            self, text="Selected Reading Detail", padding=8
        )
        detail_frame.pack(fill="both", expand=False, padx=14, pady=(0, 14))
        self.detail_text = tk.Text(
            detail_frame,
            height=8,
            wrap="word",
            font=("Consolas", 10),
            relief="flat",
            borderwidth=1,
        )
        self.detail_text.pack(fill="both", expand=True)

    def destroy(self) -> None:
        for session in (self.a_session, self.b_session):
            if session is not None:
                session.disconnect()
        super().destroy()

    def _endpoint_inputs(
        self,
        parent,
        start_column: int,
        title: str,
        log_var: tk.StringVar,
        device_var: tk.StringVar,
        interface_var: tk.StringVar,
        timestamp_var: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=title, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=start_column, columnspan=3, sticky="w", pady=(0, 4)
        )
        rows = (
            ("Transceiver log", log_var),
            ("Device name", device_var),
            ("Interface", interface_var),
            ("Collected at", timestamp_var),
        )
        for index, (label, variable) in enumerate(rows, start=1):
            ttk.Label(parent, text=label).grid(
                row=index, column=start_column, sticky="w", pady=4
            )
            ttk.Entry(parent, textvariable=variable).grid(
                row=index,
                column=start_column + 1,
                sticky="we",
                padx=8,
                pady=4,
            )
            if index == 1:
                self._button(
                    parent,
                    "Browse",
                    lambda var=log_var, device=device_var: self.pick_log(
                        var, device
                    ),
                    "primary-outline",
                ).grid(row=index, column=start_column + 2, pady=4)

    def pick_log(self, target: tk.StringVar, device: tk.StringVar) -> None:
        selected = filedialog.askopenfilename(
            title="Select Cisco transceiver log",
            filetypes=[
                ("Text files", "*.txt *.log"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            target.set(selected)
            if not device.get().strip():
                device.set(Path(selected).stem)
            interface_var = self.a_interface if target is self.a_log else self.b_interface
            try:
                self._apply_discovered_interface(Path(selected), interface_var, notify=False)
            except ValueError as exc:
                messagebox.showwarning("Log File Warning", str(exc), parent=self)

    def _apply_discovered_interface(
        self,
        log_path: Path,
        interface_var: tk.StringVar,
        *,
        notify: bool,
    ) -> bool:
        if not log_path.is_file():
            return False
        text = read_log_text(log_path, "Selected")
        detected = discover_interfaces(text)
        if len(detected) != 1:
            return False
        detected_interface = detected[0]
        configured = normalize_interface(interface_var.get())
        if configured.lower() == detected_interface.lower():
            return True
        if notify:
            use_detected = messagebox.askyesno(
                "Interface Mismatch",
                (
                    f"The configured interface {interface_var.get()!r} was not found in:\n"
                    f"{log_path.name}\n\n"
                    f"The log contains {detected_interface}. Use that interface?"
                ),
                parent=self,
            )
            if not use_detected:
                return False
        interface_var.set(detected_interface)
        return True

    def _confirm_interfaces(self) -> bool:
        pairs = (
            (Path(self.a_log.get().strip()), self.a_interface),
            (Path(self.b_log.get().strip()), self.b_interface),
        )
        for log_path, interface_var in pairs:
            if not log_path.is_file():
                continue
            text = read_log_text(log_path, "Selected")
            detected = discover_interfaces(text)
            configured = normalize_interface(interface_var.get())
            if detected and configured.lower() not in {
                interface.lower() for interface in detected
            }:
                if len(detected) == 1:
                    if not self._apply_discovered_interface(
                        log_path, interface_var, notify=True
                    ):
                        return False
                else:
                    messagebox.showwarning(
                        "Interface Not Found",
                        (
                            f"The configured interface {interface_var.get()!r} was not "
                            f"found in {log_path.name}.\n\n"
                            f"Detected interfaces: {', '.join(detected)}"
                        ),
                        parent=self,
                    )
                    return False
        return True

    def run_analysis(self) -> None:
        try:
            if not self.a_log.get().strip() or not self.b_log.get().strip():
                messagebox.showwarning(
                    "Missing files",
                    "Select both Endpoint A and Endpoint B transceiver log files.",
                    parent=self,
                )
                return
            if not self._confirm_interfaces():
                return
            self.endpoint_a, self.endpoint_b = analyze_logs(
                a_log=Path(self.a_log.get().strip()),
                a_device=self.a_device.get(),
                a_interface=self.a_interface.get(),
                a_collected_at=self.a_timestamp.get(),
                b_log=Path(self.b_log.get().strip()),
                b_device=self.b_device.get(),
                b_interface=self.b_interface.get(),
                b_collected_at=self.b_timestamp.get(),
            )
            self.directions = (
                build_direction("A to B", self.endpoint_a, self.endpoint_b),
                build_direction("B to A", self.endpoint_b, self.endpoint_a),
            )
            self.populate()
        except (OSError, ValueError, ParseError) as exc:
            messagebox.showerror("Analysis Error", str(exc), parent=self)
        except Exception as exc:
            messagebox.showerror("Unexpected Error", str(exc), parent=self)

    def connect_live_endpoint(self, label: str) -> None:
        if not netmiko_available():
            messagebox.showerror(
                "Netmiko Required",
                "Live SSH collection requires Netmiko.\n\n"
                "Install it with: python -m pip install netmiko",
                parent=self,
            )
            return
        username = self.ssh_username.get().strip()
        if not username:
            messagebox.showwarning(
                "Missing Username", "Enter an SSH username first.", parent=self
            )
            return
        host_var = self.a_device if label == "A" else self.b_device
        host = host_var.get().strip()
        if not host:
            messagebox.showwarning(
                "Missing Device",
                f"Enter Endpoint {label} device name or address first.",
                parent=self,
            )
            return
        try:
            port = int(self.ssh_port.get().strip())
            if port < 1 or port > 65535:
                raise ValueError
            device_type = validate_device_type(self.ssh_device_type.get())
        except ValueError:
            messagebox.showwarning(
                "Invalid SSH Port",
                "Enter a TCP port number from 1 through 65535.",
                parent=self,
            )
            return
        except SshCollectorError as exc:
            messagebox.showwarning("Invalid Device Type", str(exc), parent=self)
            return
        password = simpledialog.askstring(
            "SSH Login",
            (
                f"Enter SSH password for {username}@{host}:{port}.\n\n"
                "The password is used only for this login and is not saved."
            ),
            parent=self,
            show="*",
        )
        if password is None:
            return
        session = CiscoSshSession(
            host=host,
            username=username,
            port=port,
            device_type=device_type,
            strict_host_key=self.strict_host_key.get(),
        )
        try:
            session.connect(password)
        except SshCollectorError as exc:
            messagebox.showerror("SSH Login Failed", str(exc), parent=self)
            return
        detection_note = ""
        try:
            detected_type = session.detect_device_type()
            if detected_type:
                self.ssh_device_type.set(detected_type)
                detection_note = f" Detected platform: {detected_type}."
            else:
                detection_note = " Platform autodetect was inconclusive; using the selected device type."
        except SshCollectorError as exc:
            detection_note = f" Platform autodetect skipped: {exc}"
        if label == "A":
            self.a_session = session
        else:
            self.b_session = session
        self.ssh_status.set(
            f"Connected to Endpoint {label}.{detection_note} Click the next collection step when ready."
        )

    def discover_b_from_a(self) -> None:
        if self.a_session is None:
            messagebox.showwarning(
                "Endpoint A Not Connected",
                "Connect to Endpoint A before running CDP discovery.",
                parent=self,
            )
            return
        if not self.a_interface.get().strip():
            messagebox.showwarning(
                "Missing Interface",
                "Enter Endpoint A interface before running CDP discovery.",
                parent=self,
            )
            return
        try:
            output = self.a_session.command("show cdp neighbors detail")
            neighbor = find_cdp_link(
                output, self.a_interface.get(), self.b_device.get()
            )
        except (SshCollectorError, ValueError) as exc:
            messagebox.showerror("CDP Discovery Failed", str(exc), parent=self)
            return

        use_neighbor = messagebox.askyesno(
            "Confirm CDP Discovery",
            (
                "CDP found this read-only link relationship:\n\n"
                f"A local interface: {neighbor.local_interface}\n"
                f"B device: {neighbor.device_id}\n"
                f"B interface: {neighbor.remote_interface}\n\n"
                "Use these values for Endpoint B?"
            ),
            parent=self,
        )
        if not use_neighbor:
            return
        self.a_interface.set(neighbor.local_interface)
        self.b_device.set(neighbor.device_id)
        self.b_interface.set(neighbor.remote_interface)
        self.ssh_status.set(
            "CDP discovery applied. Connect to Endpoint B when ready."
        )

    def collect_live_endpoint(self, label: str) -> None:
        session = self.a_session if label == "A" else self.b_session
        if session is None:
            messagebox.showwarning(
                "Not Connected",
                f"Connect to Endpoint {label} before collecting optics.",
                parent=self,
            )
            return
        device_var = self.a_device if label == "A" else self.b_device
        interface_var = self.a_interface if label == "A" else self.b_interface
        endpoint_label = f"Endpoint {label}"
        interface = normalize_interface(interface_var.get())
        if not interface:
            messagebox.showwarning(
                "Missing Interface",
                f"Enter {endpoint_label} interface before collecting optics.",
                parent=self,
            )
            return
        command = build_transceiver_command(session.device_type, interface)
        confirmed = messagebox.askyesno(
            "Confirm Read-Only Command",
            (
                f"Run this command on {device_var.get().strip()}?\n\n"
                f"{command}\n\n"
                "This tool does not enter configuration mode."
            ),
            parent=self,
        )
        if not confirmed:
            return
        try:
            output = session.command(command)
            endpoint = load_endpoint_text(
                endpoint_label,
                device_var.get(),
                interface,
                output,
                datetime.now().astimezone(),
                f"SSH: {command}",
            )
        except (SshCollectorError, ValueError, ParseError) as exc:
            messagebox.showerror("Live Collection Failed", str(exc), parent=self)
            return
        if label == "A":
            self.endpoint_a = endpoint
            self.a_timestamp.set(endpoint.collected_at.isoformat(timespec="seconds"))
        else:
            self.endpoint_b = endpoint
            self.b_timestamp.set(endpoint.collected_at.isoformat(timespec="seconds"))
        self.ssh_status.set(
            f"{endpoint_label} optics collected. Build the live report after both sides are collected."
        )
        if self.endpoint_a and self.endpoint_b:
            self.build_live_report()

    def build_live_report(self) -> None:
        if not self.endpoint_a or not self.endpoint_b:
            messagebox.showwarning(
                "Live Data Incomplete",
                "Collect optics from both Endpoint A and Endpoint B first.",
                parent=self,
            )
            return
        self.directions = (
            build_direction("A to B", self.endpoint_a, self.endpoint_b),
            build_direction("B to A", self.endpoint_b, self.endpoint_a),
        )
        self.populate()
        self.ssh_status.set(
            "Live report built. Review the table, then use Export HTML to save it."
        )
        messagebox.showinfo(
            "Live Report Ready",
            "The live SSH report is ready. Use Export HTML to save it.",
            parent=self,
        )

    def populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.detail_text.delete("1.0", "end")
        self.result_details = []
        if not self.endpoint_a or not self.endpoint_b or not self.directions:
            return

        statuses = []
        for endpoint in (self.endpoint_a, self.endpoint_b):
            for reading in endpoint.metrics:
                status = self._display_status(reading.level)
                statuses.append(status)
                detail = self._metric_detail(endpoint, reading)
                self._insert_result(
                    status,
                    f"{endpoint.label}: {endpoint.device}",
                    reading.metric,
                    (
                        f"{reading.value:.2f} {reading.unit}; "
                        f"warning range {reading.low_warn:.2f} to "
                        f"{reading.high_warn:.2f}"
                    ),
                    detail,
                )

        for direction in self.directions:
            status = self._display_status(direction.status)
            statuses.append(status)
            loss = (
                f"{direction.loss_db:.2f} dB"
                if direction.loss_db is not None
                else "Unavailable"
            )
            detail = self._direction_detail(direction)
            self._insert_result(
                status,
                "Fiber Direction",
                direction.label,
                f"Estimated loss: {loss}",
                detail,
            )

        overall = (
            "ALARM"
            if "ALARM" in statuses
            else "WARN"
            if "WARN" in statuses or "INFO" in statuses
            else "PASS"
        )
        counts = {name: statuses.count(name) for name in ("ALARM", "WARN", "PASS", "INFO")}
        self.summary_text.set(
            f"Overall Status: {overall}    ALARM: {counts['ALARM']}  "
            f"WARN: {counts['WARN']}  PASS: {counts['PASS']}  INFO: {counts['INFO']}"
        )

    def _insert_result(
        self, status: str, scope: str, metric: str, preview: str, detail: str
    ) -> None:
        index = len(self.result_details)
        self.result_details.append(detail)
        self.tree.insert(
            "",
            "end",
            iid=str(index),
            values=(status, scope, metric, preview),
            tags=(status,),
        )

    @staticmethod
    def _display_status(level: str) -> str:
        return {
            "ok": "PASS",
            "warn": "WARN",
            "alarm": "ALARM",
            "missing": "INFO",
        }.get(level, "INFO")

    @staticmethod
    def _metric_detail(endpoint: EndpointReading, reading: MetricReading) -> str:
        return (
            f"{endpoint.label} - {endpoint.device} {endpoint.interface}\n"
            f"Collected: {endpoint.collected_at.isoformat()}\n"
            f"Timestamp source: {endpoint.timestamp_source}\n"
            f"Input file: {endpoint.source_file}\n\n"
            f"{reading.metric}: {reading.value:.2f} {reading.unit}\n"
            f"Low alarm: {reading.low_alarm:.2f}\n"
            f"Low warning: {reading.low_warn:.2f}\n"
            f"High warning: {reading.high_warn:.2f}\n"
            f"High alarm: {reading.high_alarm:.2f}\n"
            f"Status: {reading.level.upper()}"
        )

    @staticmethod
    def _direction_detail(direction: DirectionReading) -> str:
        tx = f"{direction.tx.value:.2f} dBm" if direction.tx else "missing"
        rx = f"{direction.rx.value:.2f} dBm" if direction.rx else "missing"
        loss = (
            f"{direction.loss_db:.2f} dB"
            if direction.loss_db is not None
            else "unavailable"
        )
        return (
            f"{direction.label}\n"
            f"Source: {direction.source_label}\n"
            f"Destination: {direction.destination_label}\n\n"
            f"Source Tx: {tx}\n"
            f"Destination Rx: {rx}\n"
            f"Estimated directional loss: {loss}\n"
            f"Status: {direction.status.upper()}\n\n"
            "This is an endpoint estimate from switch DOM readings, not an OTDR measurement."
        )

    def show_detail(self, _event=None) -> None:
        selection = self.tree.selection()
        self.detail_text.delete("1.0", "end")
        if selection:
            self.detail_text.insert("end", self.result_details[int(selection[0])])

    def export_html(self) -> None:
        if not self.endpoint_a or not self.endpoint_b:
            messagebox.showwarning(
                "Nothing to export", "Analyze both logs first.", parent=self
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save HTML report",
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            initialfile="fiber-link-report.html",
        )
        if not path:
            return
        try:
            self.last_report = write_report(
                self.endpoint_a, self.endpoint_b, Path(path)
            )
            messagebox.showinfo(
                "Saved", f"HTML report saved:\n{self.last_report}", parent=self
            )
        except OSError as exc:
            messagebox.showerror("Export Error", str(exc), parent=self)

    def open_report(self) -> None:
        if not self.last_report or not self.last_report.is_file():
            messagebox.showwarning(
                "Report Not Found",
                "Export an HTML report first.",
                parent=self,
            )
            return
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(self.last_report)
            elif system == "Darwin":
                subprocess.run(["open", str(self.last_report)], check=False)
            else:
                webbrowser.open(self.last_report.resolve().as_uri())
        except (AttributeError, OSError, ValueError) as exc:
            messagebox.showerror("Open Report Error", str(exc), parent=self)

    def clear(self) -> None:
        for session in (self.a_session, self.b_session):
            if session is not None:
                session.disconnect()
        self.a_session = None
        self.b_session = None
        self.endpoint_a = None
        self.endpoint_b = None
        self.directions = None
        self.last_report = None
        self.result_details = []
        self.tree.delete(*self.tree.get_children())
        self.detail_text.delete("1.0", "end")
        self.summary_text.set("Load two transceiver logs and run analysis.")


def main() -> None:
    App().mainloop()
