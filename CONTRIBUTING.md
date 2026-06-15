# Contributing

Contributions are welcome, particularly sanitized Cisco IOS and IOS-XE output
formats that improve parser coverage.

## Ground Rules

- Never submit credentials, management addresses, real hostnames, or raw
  operational logs.
- Replace device names, timestamps, interfaces, serial numbers, and identifying
  banners in fixtures.
- Keep collection behavior read-only and operator initiated.
- Treat live SSH support as optional; manual import must continue to work.
- Document MFA or interactive SSH behavior generically, without naming private
  identity providers or access patterns.
- Add or update tests for parser and report changes.
- Keep generated reports, executables, and build output out of commits.

## Development

```powershell
python -m unittest discover -s tests -v
python -m fiber_optics --help
```

Use synthetic values that exercise the relevant parser behavior without
reproducing private infrastructure data.
