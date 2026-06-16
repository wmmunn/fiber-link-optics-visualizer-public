# Fiber Link Optics Visualizer History

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
