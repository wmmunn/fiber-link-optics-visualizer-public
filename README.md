# Fiber Link Optics Visualizer

Fiber Link Optics Visualizer turns saved Cisco Catalyst transceiver output
from both ends of a link into a self-contained HTML report.

The report places the two endpoint threshold graphs side by side with
bidirectional optical-loss estimates in the middle. It displays temperature,
voltage, bias current, transmit power, receive power, device thresholds, and
collection timestamps.

![Sanitized dummy fiber optics report](docs/report-preview.png)

The image uses synthetic readings. A complete browsable example is available
at [examples/dummy-report.html](examples/dummy-report.html).

## Safety and Scope

- Manual log import only
- No SSH connections
- No credential collection or storage
- No device configuration changes
- Local HTML output

Directional loss is calculated from device-reported source Tx and remote Rx
values. It is an operational estimate, not an OTDR measurement, and the tool
does not impose a universal acceptable-loss threshold.

## Supported Input

The parser targets threshold-backed Cisco IOS and IOS-XE output from commands
such as:

```text
show interfaces <interface> transceiver detail
show interfaces transceiver detail
```

It supports common compact threshold tables and normalizes common Cisco
interface names, including `Gi`, `Te`, and `Twe`.

## Quick Start

Python 3.10 or newer is required.

```powershell
python fiber_link_optics_visualizer.py
```

The desktop application uses standard Tkinter. Installing `ttkbootstrap` adds
the optional themed appearance:

```powershell
python -m pip install -e ".[gui]"
fiber-optics-gui
```

In the GUI:

1. Select one sanitized or locally collected transceiver log for each endpoint.
2. Enter the endpoint labels and interfaces.
3. Optionally enter ISO 8601 collection timestamps with UTC offsets.
4. Select **Analyze Logs**.
5. Select **Export HTML** to create the report.

If a timestamp is omitted, the file modification time is used and identified
as such in the report.

## Sample Data

Synthetic files are included:

```text
sample_data/endpoint_a_sanitized.log
sample_data/endpoint_b_sanitized.log
```

They contain no live device data. Use interface `Te1/1/1` for both samples.

## Command Line

```powershell
python -m fiber_optics `
  --a-log "sample_data\endpoint_a_sanitized.log" `
  --a-device "LAB-SW-A" `
  --a-interface "Te1/1/1" `
  --a-collected-at "2026-01-15T10:30:17-05:00" `
  --b-log "sample_data\endpoint_b_sanitized.log" `
  --b-device "LAB-SW-B" `
  --b-interface "Te1/1/1" `
  --b-collected-at "2026-01-15T10:30:18-05:00" `
  --output "reports\fiber-link-report.html"
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

All committed fixtures must remain synthetic and sanitized.

## Windows Executable

Install the build dependencies and use the included PyInstaller specification:

```powershell
python -m pip install -e ".[build]"
pyinstaller --noconfirm --clean fiber_link_optics_visualizer.spec
```

The windowed executable is written to
`dist\FiberLinkOpticsVisualizer.exe`. Executables and build artifacts are not
committed.

## Privacy

Generated reports contain the endpoint names, interfaces, timestamps, and
input filenames entered by the operator. Review reports before sharing them.
Keep raw operational logs in an ignored local `input/` directory.

## License

MIT. See [LICENSE](LICENSE).

Cisco, Catalyst, IOS, and IOS-XE are trademarks of Cisco Systems, Inc. This
project is independent and is not affiliated with or endorsed by Cisco.
