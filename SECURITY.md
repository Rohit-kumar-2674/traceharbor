# Security policy

TraceHarbor 0.1.x is an early research release, not an independently audited system.
Evaluate with synthetic or non-sensitive data only.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** feature if private reporting is enabled for
this repository. If it is not available, open an issue saying only that you need a
private reporting channel, without exploit details or sensitive data. Do not put
credentials, real evidence, private URLs or personal records in an issue.

Include affected version, operating system, a minimal synthetic reproduction, impact,
and suggested mitigations through the agreed private channel. No response-time or
patch-time SLA is promised. Do not perform intrusive testing against systems you do
not control.

## Deployment boundaries

The supported runtime is a local single-user service on loopback. Do not expose it
through a reverse proxy, public tunnel, shared server, or remote listening address.
The session key is not a substitute for multi-user authentication and authorisation.
Do not disable Host/origin/token checks to make remote deployment work.

The application does not encrypt stored cases. Temporary OCR files are deleted after
processing but are not securely erased. Keep all temporary and permanent storage on
appropriately encrypted media.

See [the full threat model](docs/SECURITY_MODEL.md) for integrity limitations, parser
risks, backups, and the controls required before use with sensitive material.
