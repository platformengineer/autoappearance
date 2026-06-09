# Security Policy

## Supported Versions

Security fixes are handled for the current `main` branch and the latest
published package version.

## Reporting a Vulnerability

Please do not open a public issue for security-sensitive reports.

Instead, use GitHub private vulnerability reporting if it is enabled for the
repository, or contact the maintainers privately with:

- A description of the issue.
- Steps to reproduce, if available.
- The impact you believe it has.
- Any suggested fix or mitigation.

The maintainers will acknowledge the report, investigate, and coordinate a fix
before public disclosure when appropriate.

## Scope

AutoAppearance runs local `busctl` commands to read the desktop portal
appearance setting and writes Sublime Text preferences. Relevant reports may
include command execution risks, unsafe file handling, or behavior that could
unexpectedly modify user settings.
