# AGENTS.md — Rules for AI agents working on jolarca-consent

This file is the highest-leverage context for every AI agent session. Read it first.

## Tech stack

- **Python 3.12** (required)
- **Django 5.2** + **Django REST Framework** + **drf-spectacular** (OpenAPI)
- **PostgreSQL** (psycopg3)
- **structlog** (structured logging)
- **Celery + Redis** (async tasks, if needed)
- **ruff** (linting + formatting, line-length 100)
- **mypy --strict** (type checking)
- **pytest** (testing)
- **pre-commit** (git hooks)

## Commands

```bash
# Setup
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Pre-merge gate (MUST pass)
make check

# Individual checks
ruff check --fix
ruff format
mypy --strict
pytest

# Run the service
python manage.py runserver

# Verify hash chain
python scripts/verify_chain.py
```

## Code conventions

- **Line length:** 100 characters (ruff enforced)
- **Type hints:** Required everywhere (mypy --strict)
- **Docstrings:** Required for all public functions/classes (Google style)
- **Named exports:** No `from module import *`
- **Error handling:** Use custom exception classes; never swallow exceptions silently
- **Logging:** Use structlog; never use `print()` in production code
- **Tests:** Colocate with source (`tests/` directory); use pytest fixtures

## Boundaries (hard rules)

1. **No personal data in git.** No fixtures containing real personal data; tests use synthetic data only. `.env` never committed.
2. **No secrets in code.** API keys, passwords, tokens — all via Vault, injected at runtime.
3. **Append-only is sacred.** The consent ledger is append-only. ORM guard + DB-level enforcement. ORM-only is insufficient.
4. **Hash chain is sacred.** Every record is part of the SHA-256 chain. Any modification breaks the chain. The offline verifier must pass.
5. **No bare `TBD`.** Unsourced legal values must be `[COUNSEL-TO-CONFIRM]`.
6. **Conventional Commits.** Every commit follows the Conventional Commits spec. Every change appears in `CHANGELOG.md`.
7. **CI actions pinned by SHA.** GitHub Actions are pinned by commit SHA with a trailing version comment. Least-privilege `permissions:` on every job.
8. **No force-push, no history rewrite.** `main` is protected. Git history is audit history.

## Compliance posture

| Standard | Anchor controls |
|---|---|
| GDPR | Art. 7(1) demonstrability, Art. 17 erasure (via anonymize-don't-delete) |
| ISO 27001 | A.8.12 data integrity, A.8.9 configuration management |
| SOC 2 | CC7.x system operations (separation of duties) |

## Escalation

Stop and ask when:
- Two sources of truth conflict
- A legal value has no source
- A change would weaken an existing control
- Live data migration risks irreversible loss
- A defect in the design no longer reproduces

Present evidence, options, and a recommendation — then wait.

## References

- `docs/architecture.md` — system context and components
- `docs/threat-model.md` — threats and mitigations
- `docs/migration-plan.md` — cutover strategy
- `docs/adr/` — architecture decision records
- `docs/kickoff-prompt.md` — the original task prompt
