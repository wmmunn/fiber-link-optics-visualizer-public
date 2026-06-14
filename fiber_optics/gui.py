from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import ttkbootstrap as tb

    TTKBOOTSTRAP_AVAILABLE = True
except Exception:
    tb = None
    TTKBOOTSTRAP_AVAILABLE = False

from .analysis import build_direction
from .models import DirectionReading, EndpointReading, MetricReading
from .interfaces import normalize_interface
from .parser import ParseError, discover_interfaces
from .workflow import analyze_logs, write_report


APP_NAME = "Fiber Link Optics Visualizer"
APP_VERSION = "0.2"


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
        self.summary_text = tk.StringVar(
            value="Load two transceiver logs and run analysis."
        )

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
            text="Manual log import; no device connections or credential storage.",
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
            self._apply_discovered_interface(Path(selected), interface_var, notify=False)

    def _apply_discovered_interface(
        self,
        log_path: Path,
        interface_var: tk.StringVar,
        *,
        notify: bool,
    ) -> bool:
        if not log_path.is_file():
            return False
        text = log_path.read_text(encoding="utf-8-sig", errors="replace")
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
            text = log_path.read_text(encoding="utf-8-sig", errors="replace")
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
            os.startfile(self.last_report)
        except OSError as exc:
            messagebox.showerror("Open Report Error", str(exc), parent=self)

    def clear(self) -> None:
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
