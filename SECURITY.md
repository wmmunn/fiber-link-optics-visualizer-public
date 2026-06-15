# Security

This project processes local text files and can optionally connect to network
devices for read-only SSH collection when the operator enables that workflow.
Do not place credentials or unsanitized operational logs in the repository.

Reports contain the device names, interfaces, timestamps, and input filenames
supplied by the operator. Review generated reports before sharing them.

The live SSH workflow prompts at runtime and does not store credentials.
MFA and interactive SSH behavior varies by environment; use the manual import
workflow whenever direct collection is not approved or practical.

Please report security issues privately to the repository owner rather than
opening a public issue containing sensitive data.
