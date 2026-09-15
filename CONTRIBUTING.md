# Contributing

Build features that make evidence easier to understand and verify. Prefer small,
reviewable changes, explicit limitations, and reproducible tests.

1. Open a non-sensitive issue explaining the user problem and proposed scope.
2. Make a branch, use the documented Python environment, and keep changes focused.
3. Add tests for success, failure, malformed inputs, and privacy/security boundaries.
4. Run `python -m pytest`, `ruff check traceharbor tests`, and the relevant browser checks.
5. Document any network requests, data retention, third-party transfers or credentials.
6. Open a PR with screenshots for UI work and the exact tests actually run.

## Design principles

- Findings are human assessments; tool output must never imply guilt or identity.
- New tools stay offline by default. Any network feature needs an explicit user
  action, destination disclosure, input limits, SSRF protection, timeouts and tests.
- Do not add covert surveillance, facial identification, private-account bypasses,
  mass personal-profile scraping, or people-ranking/risk-scoring features.
- Preserve original bytes; make derivations explicit. Never silently mutate evidence.
- Use synthetic fixtures. No real cases, credentials, contact lists or personal images.
- Do not claim a feature is tested, encrypted, compliant, production-ready or
  forensic-grade unless there is concrete evidence supporting that exact claim.

Node/Playwright are development-only dependencies; keep the browser runtime free of
external scripts, fonts and CDN requests. Use accessible labels, keyboard interactions,
proper empty/error states and narrow-screen layouts.

Contributions are provided under the repository's MIT license. Be respectful and
constructive; discuss technical issues without harassment or personal attacks.
