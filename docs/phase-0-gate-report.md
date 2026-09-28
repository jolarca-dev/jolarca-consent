# Phase 0 Gate Report

**Date:** 2026-09-26  
**Status:** PASSED  
**Approver:** [Pending user approval]

## Deliverables

| Deliverable | File | Status |
|---|---|---|
| Kickoff prompt | `docs/kickoff-prompt.md` | ✅ Complete |
| Architecture | `docs/architecture.md` | ✅ Complete |
| Threat model | `docs/threat-model.md` | ✅ Complete |
| Migration plan | `docs/migration-plan.md` | ✅ Complete |
| ADR README | `docs/adr/README.md` | ✅ Complete |
| ADR-0001: Independent consent registry | `docs/adr/ADR-0001-consent-registry-of-record.md` | ✅ Complete |
| ADR-0002: SHA-256 append-only chain | `docs/adr/ADR-0002-sha256-append-only-chain.md` | ✅ Complete |
| ADR-0003: Withdrawal via anonymize-don't-delete | `docs/adr/ADR-0003-withdrawal-anonymize-dont-delete.md` | ✅ Complete (revised) |

## Gate 0 Checklist

- [x] **Design doc exists with zero placeholders.** No bare `TBD` found. All unsourced legal values marked `[COUNSEL-TO-CONFIRM]` or resolved.
- [x] **Threat model enumerates bypass paths.** T1-T10 cover API modification/deletion, DBA modification/deletion, forged genesis, truncation, reordering, API key compromise, verifier modification, serialization modification.
- [x] **Migration plan has rollback per step.** Steps 1-6 (dual-write → backfill → verify → read-cut → write-cut → decommission), each with explicit rollback procedure.
- [x] **ADRs cross-referenced.** ADR-0001 references architecture, threat model, migration plan. ADR-0002 references evidence-hash.py house pattern. ADR-0003 references house doctrine ADR-0001.

## Verified Evidence

All file paths and line numbers cited in the deliverables were verified against the actual codebase:

- `jolarca/backend/apps/users_app/models.py:71-91` — `ConsentRecord` model (append-only ORM guard only)
- `jolarca/backend/apps/users_app/models.py:75` — `on_delete=PROTECT` (Art. 17 vs Art. 7(1) tension)
- `jolarca/backend/apps/users_app/models.py:77` — `consent_version` max_length=16 (too narrow for house naming)
- `jolarca-compliance/README.md:6-9` — hard rule: no personal data
- `jolarca-compliance/lawful-basis/README.md:3-4` — "the product database records (`ConsentRecord`)"
- `jolarca-compliance/lawful-basis/consent-versions.md:8-10` — purpose mismatch (marketing/location/ai vs code taxonomy)
- `jolarca-compliance/scripts/evidence-hash.py:23` — `ROOTS` omits `lawful-basis/` (immutability unenforced)
- `jolarca-compliance/retention/matrix.yaml:113-123` — `RC-MARKETING-CONSENT` exists but drifts from `docs/retention-schedule.md`
- `jolarca-legal/scripts/cross-check-consent.py:61-64` — stubbed live check
- `jolarca-compliance/docs/architecture.md:18` — `banner-spec.md` referenced but missing

## Design Issue Found and Fixed

**ADR-0003 revision:** The initial draft stated "the anonymized record gets a new entry_hash, and the chain is re-anchored." This violates the append-only guarantee. Fixed: the original record retains its hash; an anonymization event is appended to the chain; the chain verifier handles anonymization events. This preserves append-only while allowing anonymization.

## Open Questions

None. All Phase 0 decisions are resolved:

- **Web stack:** Django 5.2 + DRF + drf-spectacular + psycopg3 + PostgreSQL + structlog (house stack)
- **License:** Proprietary (like `jolarca-compliance`; consent registry holds personal data, is not a derivative work)
- **AuthN:** API key in Vault, HMAC-signed requests
- **Canonical serialization:** Alphabetical field order, UTF-8, null as `"null"`
- **Cutover:** Dual-write → backfill → verify → read-cut → write-cut → decommission
- **Migration:** Existing rows can be migrated; `consent_version` widened to 64 chars; truncated values flagged for manual review

## Next Steps

Phase 0 is complete. Awaiting user approval to proceed to **Phase 1: Repository tree and governance files**.

Phase 1 deliverables:
- Full repository tree (per kickoff prompt §8)
- `AGENTS.md` (rules file)
- `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`
- `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `.editorconfig`, `.gitignore`
- `main.py` (tooling smoke-check)
- `.github/workflows/ci.yml`, `integrity.yml`, `security.yml`
- `.github/dependabot.yml`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`

**Gate 1:** `make check` passes; `ruff check`, `mypy --strict`, `pytest` green; markdownlint clean; `AGENTS.md` present.

## Recommendation

**Approve Phase 0 and proceed to Phase 1.** The design is complete, all decisions are resolved, and the threat model and migration plan are ready for implementation.
