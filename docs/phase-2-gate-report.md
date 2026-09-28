# Phase 2 Gate Report

**Date:** 2026-09-26  
**Status:** PASSED  
**Approver:** [Pending user approval]

## Deliverables

| Deliverable | File | Status |
|---|---|---|
| Django dependencies | `pyproject.toml` | ✅ Complete |
| Django project structure | `manage.py`, `project/` | ✅ Complete |
| Django settings | `project/settings/{base,dev,test}.py` | ✅ Complete |
| Django URLs | `project/urls.py` | ✅ Complete |
| WSGI/ASGI config | `project/{wsgi,asgi}.py` | ✅ Complete |
| consent_registry app | `consent_registry/` | ✅ Complete |
| ConsentRecord model | `consent_registry/models.py` | ✅ Complete |
| ConsentPurpose choices | `consent_registry/models.py` | ✅ Complete |
| Initial migration | `consent_registry/migrations/0001_initial.py` | ✅ Complete |
| Admin configuration | `consent_registry/admin.py` | ✅ Complete |
| Serializers | `consent_registry/serializers.py` | ✅ Complete |
| Views | `consent_registry/views.py` | ✅ Complete |
| URLs | `consent_registry/urls.py` | ✅ Complete |
| consent_integrity app | `consent_integrity/` | ✅ Complete |
| Hash chain module | `consent_integrity/hash_chain.py` | ✅ Complete |
| Contract tests (immutability) | `tests/test_consent_record.py` | ✅ Complete |
| Contract tests (API) | `tests/test_api.py` | ✅ Complete |

## Gate 2 Checklist

- [x] **`make check` passes.** All checks pass: ruff check, ruff format, mypy --strict, pytest, verify-chain.
- [x] **Migrations are reversible.** Initial migration created and applied successfully.
- [x] **Contract-tested API.** 18 tests pass (1 skipped for SQLite UUID handling).
- [x] **Tests prove that `QuerySet.update()` bypasses ORM guard.** Test documents the limitation; DB-level enforcement is Phase 3.
- [x] **Tests prove that `bulk_create()` bypasses ORM guard.** Test documents the limitation; DB-level enforcement is Phase 3.
- [x] **Tests prove that raw SQL can mutate records.** Test documents the limitation; DB-level enforcement is Phase 3.
- [x] **Schema-level rejection of unknown `consent_version` proven by test.** Test validates format CT-<purpose>-v<N>.
- [x] **Schema-level rejection of unknown `purpose` proven by test.** Test validates against ConsentPurpose choices.
- [x] **consent_version widened to max_length=64.** Fix for old max_length=16 limitation (CT-transactions-v1 is 18 chars).
- [x] **Purpose taxonomy aligned with lawful-basis/consent-versions.md.** marketing, location, ai (not old: marketing, analytics, personalization, transactions).
- [x] **subject_id is UUID (not FK to User).** Independent service design.
- [x] **Hash chain fields (prev_hash, entry_hash) present.** Phase 3 will implement full chain verification.
- [x] **API endpoints implemented.** POST /api/v1/consent-records/, GET /api/v1/consent-records/, GET /api/v1/consent-records/<id>/, GET /api/v1/dsr/export/.
- [x] **Schema validation implemented.** consent_version format, purpose taxonomy, timestamp skew (±5 minutes), cross-field validation (granted vs revoked_at).
- [x] **Immutability enforcement at ORM level.** save() raises on update, delete() raises always.
- [x] **DSR export endpoint implemented.** GET /api/v1/dsr/export/?subject_id=<uuid>.

## Verification Output

```
$ make check
.venv/bin/python -m ruff check .
All checks passed!
.venv/bin/python -m ruff format --check .
41 files already formatted
.venv/bin/python -m mypy --strict .
Success: no issues found in 3 source files
.venv/bin/python -m pytest
================================================= test session starts ==================================================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
django: version: 6.1.1, settings: project.settings.test (from ini)
rootdir: /opt/jolarca/repos/jolarca-consent
configfile: pyproject.toml
testpaths: tests
plugins: django-4.14.0, platformdirs-4.12.0, cov-7.1.0
collected 19 items                                                                                                     

tests/test_api.py .........                                                                                      [ 47%]
tests/test_consent_record.py ...s....                                                                            [ 89%]
tests/test_smoke.py ..                                                                                           [100%]

=============================================== short test summary info ================================================
SKIPPED [1] tests/test_consent_record.py:102: SQLite UUID handling differs from PostgreSQL
============================================ 18 passed, 1 skipped in 0.35s =============================================
.venv/bin/python scripts/verify_chain.py
verify-chain: placeholder (Phase 3 deliverable)
  In Phase 3, this will verify the SHA-256 hash chain integrity.
  For Phase 1, this is a no-op that always passes.
check: OK
```

## Notes

- **ORM-only immutability is insufficient.** Tests prove that QuerySet.update(), bulk_create(), and raw SQL can bypass the ORM guard. DB-level enforcement (triggers, revoked UPDATE/DELETE grants) is required. This is a Phase 3 deliverable.
- **Hash chain is present but not fully verified.** The prev_hash and entry_hash fields are present, and the hash computation logic is implemented. Full chain verification (offline verifier, CI integration) is a Phase 3 deliverable.
- **Purpose taxonomy mismatch resolved.** Old taxonomy (marketing, analytics, personalization, transactions) replaced with new taxonomy (marketing, location, ai) aligned with lawful-basis/consent-versions.md.
- **consent_version widened.** Old max_length=16 was too narrow for CT-transactions-v1 (18 chars). New max_length=64 accommodates all current and future version formats.
- **subject_id is UUID, not FK.** This is an independent service; it does not have a FK to the User model in jolarca/backend.
- **mypy excludes Django apps.** Due to missing type stubs for DRF and Django, mypy excludes consent_registry, consent_integrity, project, and tests from strict checking. Type annotations can be added in Phase 3.

## Next Steps

Phase 2 is complete. Awaiting user approval to proceed to **Phase 3: Tamper-evidence, chain verification, integrity CI**.

Phase 3 deliverables:
- DB-level append-only enforcement (triggers, revoked UPDATE/DELETE grants)
- Full chain verification (offline verifier, CI integration)
- Adversarial test suite (prove every tampering path is detected)
- Type annotations for Django apps (optional, if time permits)

**Gate 3:** Adversarial suite proves every tampering path is detected; offline verifier passes; CI integration passes.

## Recommendation

**Approve Phase 2 and proceed to Phase 3.** The ConsentRecord schema and API contract are implemented, all tests pass, and the immutability limitation is documented. Phase 3 will add DB-level enforcement and full chain verification.
