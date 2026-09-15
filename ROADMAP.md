# Roadmap

Items below are future work, not existing features. No release dates are promised.

## 0.1 — foundation (implemented)

- Local cases, immutable evidence records, source references, findings and events
- Original-byte hashes, image metadata, dHash and optional local OCR
- Local integrity verification and portable reports
- Responsive browser workspace and CLI
- Input limits, loopback session security and automated core/API tests

## Next: validate and harden

- Run and refine cross-browser and Android end-to-end tests on real devices
- Independent security review and hostile file-format testing
- Dependency vulnerability auditing and locked transitive dependency maintenance
- Encrypted case storage with a reviewed key-management design
- Signed exports with independently retained verification keys and trusted timestamps
- Safe backup/restore with crash, rollback and migration tests
- Redaction previews and explicit per-field export controls
- Retention rules, recoverable deletion and auditable disposal workflows
- Reproducible builds and signed release artifacts

## Later: research capabilities

- Carefully scoped PDF/document metadata and text extraction in an isolated parser
- Reviewed public DNS/RDAP adapters for domains, with opt-in requests and provenance
- User-created evidence relationship views without automated identity attribution
- Additional local OCR languages with clearly documented model limitations
- Import of user-owned evidence exports with schema/size/path/integrity validation

## Before any operational police deployment

Agree an independently reviewed threat model and lawful collection process; validate
tools against known reference datasets; establish access controls, encryption,
retention, incident response, chain-of-custody procedures, operator training and
human review. This repository cannot certify its own suitability.
