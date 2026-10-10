# Changelog

All notable changes to this repository are documented here.
Format: [Conventional Commits](https://www.conventionalcommits.org). Every
compliance-relevant change must appear here.

## [Unreleased]

### Added

- chore: repository skeleton per Phase 0 design (architecture, threat model, migration plan, ADRs).
- docs: architecture, threat model, migration plan, ADR-0001 (independent consent registry), ADR-0002 (SHA-256 append-only chain), ADR-0003 (withdrawal via anonymize-don't-delete).
- docs: ADR-0004 — GDPR Art. 37 DPO assessment (not required; sole operator holds all GDPR obligations).
- docs: cross-service DSAR runbook (`docs/dsar-runbook.md`) — Art. 15/16/17/18/20/21 procedure covering jolarca-consent, jolarca, Redis, logs, and backups within the 30-day deadline.
- docs: breach runbook (`docs/breach-runbook.md`) — incident response mapping T1–T10 to 72-hour GDPR Art. 33 notification, with 24-hour target for Critical severity.
- ci: initial workflows (ci.yml, integrity.yml, security.yml), dependabot, issue/PR templates.
- tooling: Makefile, pyproject.toml, .pre-commit-config.yaml, .editorconfig, AGENTS.md.
- feat: per-purpose retention TTLs with scheduled anonymization job (`manage.py anonymize_expired`). TTLs: marketing 730d, location 365d, ai 365d (all `[COUNSEL-TO-CONFIRM]`). Implements ADR-0003 anonymize-don't-delete for records past retention period.
- feat: `anonymized_at` field on ConsentRecord model with migration (0003).

### Changed

- docs: replaced fictional DPO/compliance-lead role references with controller (`@JourneyOfLife`) across README, CONTRIBUTING, PR template, architecture, migration plan, and ADR index (per ADR-0004).
- fix: replaced `security@journeyoflife.example` (RFC 2606 reserved domain, non-routable) with `security@jolarca.com` in SECURITY.md — same defect class as fictional DPO contact.
- docs: strengthened ADR-0004 reassessment triggers (7 event-driven + 12-month calendar); added KYC/Art. 9 caveat to criterion (c).
- fix(ci): `mypy --strict .` → bare `mypy --strict` — path argument overrode `[tool.mypy].files` config, checking 15 files with 16 errors instead of the 4 configured files (audit A-11).
- fix(ci): `pytest` → `pytest --cov --cov-fail-under=80` — CI was not enforcing the coverage floor (audit A-10).
- fix: offline chain verifier (`scripts/verify_chain.py`) now handles anonymized records — skips `entry_hash` recomputation for records with `anonymized_at IS NOT NULL` while still verifying `prev_hash` chain continuity.
