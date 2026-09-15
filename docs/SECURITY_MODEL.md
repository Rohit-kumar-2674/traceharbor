# Threat model and integrity boundaries

## Intended environment

One operator on a trusted local device, using synthetic/non-sensitive training
material. The production CLI binds only to 127.0.0.1. Never expose it using a public
tunnel, network interface, shared desktop service or reverse proxy.

## Protected assets

Original files, analyst notes, source URLs, metadata, OCR text, case purpose,
local activity records and the per-process API session key.

## Controls in this release

- Random 256-bit session token, generated anew at startup
- Bearer-token API authentication, constant-time token comparison
- Explicit Host allowlist, Origin and Sec-Fetch-Site checks, no permissive CORS
- Restrictive CSP, no third-party browser assets, escaped user text
- Exact static-asset allowlist; originals are authenticated attachment downloads
- Original filenames are not used as vault paths; blob paths are SHA-256 digests
- JSON request limits, file-size limits and image decompression-bomb checks
- Validated HTTP(S) source strings; no server-side URL fetching or DNS resolution
- Tesseract invoked as an argument list, never a shell; input is decoded/re-encoded
- Two concurrent analysis slots, OCR timeout, single-user server concurrency limit
- SQLite transactions and process-local locks for writes and verified exports
- Original hash checks before download, comparison and export
- New storage directories/files use restrictive permissions on POSIX systems

## What verification means

Records are canonical JSON (`sort_keys=True`, UTF-8, compact separators). Each audit
event stores the record ID, record hash, preceding event hash, sequence number,
local timestamp and action. `verify` recomputes the linked hashes, checks the current
record inventory against the most recent event for each record, and hashes originals.

This detects accidental corruption or partial/uncoordinated modifications. It does
**not** defeat someone who can rewrite both records and all associated hashes. It
does not prove where the file originated, who collected it, whether the clock was
correct, or whether the contents are true. A missing entire case may not be detected
from the remaining database alone. External anchors and signed, independently kept
manifests are not implemented.

Only the application append API is immutable. SQLite files and blob storage are
writable by the local OS account. The analyst label is not cryptographic identity.

## Known residual risks

- No application-level encryption, authenticated multi-user roles, secure deletion,
  key recovery, signed timestamps, secure case imports, or automatic redaction
- Local malware or another privileged process can read storage and session state
- Untrusted file parsers can have vulnerabilities despite input limits; no process
  sandbox or container isolation is provided for Pillow/Tesseract
- OCR uses temporary files which are removed but not securely erased
- The browser briefly receives the session key in the URL fragment; it is removed
  immediately. A malicious browser extension or compromised page could steal it
- HTTP over loopback is not TLS; the service is not designed for remote access
- Source links may reveal browser/network information when opened manually
- Exported notes, raw EXIF and OCR can contain sensitive information
- Local resource exhaustion remains possible; this is not a hostile multi-user server
- The process lock does not coordinate multiple independently started servers using
  the same vault. Run only one server/CLI writer per vault at a time
- Crash-safe blob/DB reconciliation and whole-vault backup/restore tooling are future work

## Before real sensitive use

Obtain independent assessment. At minimum review encryption, access control, parser
isolation, dependency vulnerabilities, evidence acquisition validation, external
integrity anchoring, retention, backups, audit identity and incident response.
Technical controls do not establish legal authority. Use an organisation-approved
forensic workflow rather than treating the software as a substitute for one.
