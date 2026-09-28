# jolarca-consent

**PRIVATE repository.** Independent consent registry of record for the Journey Of Life marketplace platform (LT / LV / EE markets).

> Hard rule: this repository is the **system of record** for consent records. Consent records are personal data (GDPR Art. 4(1)). The registry is tamper-evident (SHA-256 hash chain) and independently owned (separate from the product that needs consent).

## Purpose

`jolarca-consent` extracts `ConsentRecord` out of the marketplace application into a separately owned, tamper-evident service whose entries cannot be modified by the party that needs consent.

**Why a separate service:** The marketplace application currently owns both the consent UX (the party that needs consent) and the consent record (the proof of consent). Whoever controls the app database controls the evidence. That defeats **GDPR Art. 7(1)** demonstrability, **ISO 27001 A.8.12** integrity, and **SOC 2 CC7.x**, because the control and the thing it constrains share an owner.

## Access

| Role | Access | Notes |
|---|---|---|
| DPO | Admin | Required reviewer on all compliance artifacts |
| Compliance lead | Admin | Required reviewer on all compliance artifacts |
| Engineering leads | Write | Via PR only; branch protection enforced |
| Everyone else | None | Requests via issue, SLA: 2 business days |

## Structure

| Path | Content |
|---|---|
| `docs/` | Architecture, threat model, migration plan, ADRs |
| `src/` | Django project (consent_registry, consent_integrity apps) |
| `scripts/` | Offline chain verifier, migration scripts, DSR export |
| `tests/` | Unit, contract, integration, adversarial tests |
| `.github/` | CI workflows, dependabot, issue/PR templates |

## Hard rules (non-negotiable)

1. **Append-only, enforced in depth.** ORM guard *and* DB-level protection (revoked `UPDATE`/`DELETE` grants for the application role). ORM-only is explicitly insufficient.
2. **Hash chain.** Each entry carries `prev_hash` and `entry_hash` (SHA-256 over canonical serialization). Genesis entry defined. Chain must be independently verifiable offline by a stdlib-only script.
3. **Withdrawal ≠ deletion.** Art. 7(1) requires proving consent was given; Art. 17 grants erasure. Resolve via **anonymize-don't-delete**: anonymize the subject identifier, retain purpose, version, timestamp, and the fact of grant/withdrawal.
4. **No personal data in git.** No fixtures containing real personal data; tests use synthetic data only. `.env` never committed.
5. **Conventional Commits.** Every commit follows the Conventional Commits spec. Every change appears in `CHANGELOG.md`.
6. **CI actions pinned by SHA.** GitHub Actions are pinned by commit SHA with a trailing version comment. Least-privilege `permissions:` on every job.
7. **No force-push, no history rewrite.** `main` is protected. Git history is audit history.

## Key SLAs

| Obligation | Deadline | Monitor |
|---|---|---|
| Chain verification | Every deployment + daily schedule | `integrity.yml` |
| Critical CVE fix | ≤ 7 days | `security.yml` |
| DSR export | 30 days (GDPR Art. 12) | Manual + API |

## Contacts

- **DPO:** dpo@journeyoflife.example
- Security incidents: see `SECURITY.md`

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
make check                # full static verification gate
```

## Compliance posture

| Standard | Anchor controls |
|---|---|
| GDPR | Art. 7(1) demonstrability, Art. 17 erasure (via anonymize-don't-delete) |
| ISO 27001 | A.8.12 data integrity, A.8.9 configuration management |
| SOC 2 | CC7.x system operations (separation of duties) |

## References

- `docs/architecture.md` — system context and components
- `docs/threat-model.md` — threats and mitigations
- `docs/migration-plan.md` — cutover strategy
- `docs/adr/` — architecture decision records
