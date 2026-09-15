# Validation record — v0.1.0

This records checks actually run during initial authoring. It is not a security
audit, performance guarantee or forensic validation.

## Completed

- Linux / Python 3.12.14
- Pillow 12.3.0 and Tesseract 5.3.4
- 42 passing pytest cases across `tests/test_core.py` and `tests/test_api.py`
- Real local OCR of a generated, non-personal training image
- Original-byte SHA-256/SHA-512 comparison against Python hashlib
- SQLite persistence and reference isolation between cases
- UTC event conversion, archive/reopen and retained original access
- Detection of altered files, altered records and removed audit entries
- Export contents/checksums and opt-in inclusion of originals
- HTML escaping of synthetic script/image-like text
- API authentication, Host/origin checks, JSON/body limits and malformed inputs
- Analysis-only processing does not retain original bytes or create cases
- Python lint/format checks and JavaScript syntax checks
- Wheel build and installation without an editable checkout; the installed CLI,
  health/status/schema endpoints and all four packaged interface assets were checked
  from outside the source directory

## Not completed here

- Live desktop/mobile browser evaluation: the authoring browser could not reach the
  local loopback server (`ERR_BLOCKED_BY_CLIENT`)
- The included Playwright smoke suite: supplied for repeatable testing, not marked passed
- Installation on a physical Android, Windows or macOS device
- Independent security assessment, dependency CVE audit, parser sandbox testing,
  load testing, accessibility audit or operational forensic acceptance testing

The repository's GitHub Actions workflow can run repeatable core checks after upload.
Do not treat configuration of a workflow as evidence it has passed; inspect its actual
run result. Browser tests require their separate development setup.
