# Fiber Link Optics Visualizer History

## Next

- Added post-login `show version` platform autodetection for live SSH sessions
  so IOS, IOS-XE, and NX-OS devices can use the correct read-only transceiver
  command after connection.
- Treat transceiver modules that explicitly do not support DOM/DDM readings as
  limited data, allowing reports to be generated without false optic warnings.

## 0.3.5 - 2026-06-16

- Added Nexus-style `SFP Detail Diagnostics Information` parsing so row-based
  DOM output can be analyzed alongside Catalyst-style transceiver detail.
- Added a supported-platform dropdown for live SSH collection and limited it to
  the validated choices `cisco_ios`, `cisco_xe`, and `cisco_nxos`.
- Routed Nexus live collection to `show int <interface> transceiver details`
  while preserving the Catalyst-style command path for IOS and IOS-XE.
- Sanitized CDP-discovered B-side device names before applying them to the host
  field by trimming domain suffixes and parenthetical trailer text that can
  interfere with SSH connection attempts.
- Normalized `Ethernet` and `Eth` interface names consistently so Nexus-style
  interfaces line up across CDP output, operator input, and parsed logs.
- Kept the public package sanitized and source-only, with synthetic fixtures and
  no environment-specific identifiers or binary release artifacts committed.

## 0.3.4 - 2026-06-16

- Synced the public package to the latest sanitized working build.
- Added file-size limits and strict UTF-8 decoding for safer log handling.
- Added Netmiko device-type validation and a strict host-key verification
  toggle without changing the default SSH behavior.
- Improved report opening compatibility across Windows, macOS, and Linux.
- Updated the GUI layout to behave better under Windows resolution scaling.
- Kept the public package sanitized by omitting environment-specific names,
  provider-specific MFA wording, and unsigned binary distribution.

## 0.3.2 - 2026-06-15

- Added optional read-only SSH collection.
- Added separate Endpoint A and Endpoint B interactive logins.
- Added CDP-assisted B-side discovery and operator confirmation.
- Added live report labeling for SSH-collected runs.
- Added public documentation for optional SSH collection and generic MFA notes.

## 0.2.0 - 2026-06-14

- Published the initial public release.
- Included manual log import, HTML reporting, sanitized sample data, tests,
  and PyInstaller build metadata.
