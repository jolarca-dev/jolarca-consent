# ADR-0001: Independent consent registry of record

## Status

Accepted

## Context

The marketplace application (`jolarca/backend/apps/users_app/models.py:71-91`) currently owns both the consent UX (the party that needs consent) and the consent record (the proof of consent). Whoever controls the app database controls the evidence.

This creates several compliance problems:

1. **GDPR Art. 7(1)** requires the controller to demonstrate that consent was given. If the party that needs consent also owns the proof, the demonstrability is undermined by a conflict of interest.

2. **ISO 27001 A.8.12** (data integrity) requires controls to prevent unauthorized modification. If the same team that develops the consent UX can modify the consent records, the control is weakened.

3. **SOC 2 CC7.x** (system operations) requires separation of duties. The party that needs consent should not be the party that owns the proof.

4. **Immutability is ORM-convention only.** The current `ConsentRecord.save()` raises on update, but this can be bypassed via `QuerySet.update()`, `bulk_create`, or raw SQL. There is no cryptographic proof of immutability.

5. **`jolarca-compliance` cannot store consent records.** The compliance repository has a hard rule: "governance artifacts only — policies, registers, anonymized indexes, hashes, and evidence references. It must **never** contain raw personal data" (`README.md:6-9`). Consent records are personal data (GDPR Art. 4(1)), so they cannot live in `jolarca-compliance`.

6. **`jolarca-legal`'s re-consent control is stubbed.** The `cross-check-consent.py` script is blocked on a registry API that does not exist (`scripts/cross-check-consent.py:61-64`).

## Decision

Extract `ConsentRecord` into a separate, independently owned service: `jolarca-consent`.

**Key properties:**
- **Independent ownership:** The consent registry is owned by a separate team (or at least, a separate deployment) from the product. The product team cannot modify the registry's code or database.
- **Tamper-evident:** Every consent record is part of a SHA-256 hash chain. Any modification breaks the chain and is detected by the offline verifier.
- **Append-only, enforced in depth:** ORM guard *and* DB-level protection (revoked `UPDATE`/`DELETE` grants). ORM-only is explicitly insufficient.
- **System of record:** The consent registry is the authoritative source of truth for consent state. The product may cache, but the cache is non-authoritative.

**Boundary:**
- `jolarca-consent` owns consent **records** (personal data)
- `jolarca-compliance` owns consent **texts** (governance, no personal data)
- `jolarca` (product) owns consent **UX** and enforcement

## Consequences

**Positive:**
- Separation of duties: the party that needs consent does not own the proof
- Tamper-evident: cryptographic proof of immutability
- Compliance: satisfies GDPR Art. 7(1), ISO 27001 A.8.12, SOC 2 CC7.x
- Enables `jolarca-legal`'s re-consent control to go live

**Negative:**
- Adds operational complexity: a new service to deploy, monitor, and maintain
- Adds latency: consent queries now require a network call
- Requires migration: existing `ConsentRecord` rows must be migrated to the new registry

**Neutral:**
- The product team must adapt to calling an API instead of querying a local table
- The compliance team must update ROPA, DPIA, retention schedule, and architecture docs

## Compliance mapping

| Control | How satisfied |
|---|---|
| GDPR Art. 7(1) | Registry is system of record; hash chain provides cryptographic proof |
| ISO 27001 A.8.12 | Hash chain + DB-level append-only + offline verifier |
| SOC 2 CC7.x | Separation of duties: product needs consent but does not own the proof |

## References

- `jolarca-compliance/README.md:6-9` — hard rule: no personal data
- `jolarca/backend/apps/users_app/models.py:71-91` — current `ConsentRecord` model
- `jolarca-legal/scripts/cross-check-consent.py:61-64` — stubbed re-consent control
- `docs/architecture.md` — system context and trust model
- `docs/threat-model.md` — threats and mitigations
- `docs/migration-plan.md` — cutover strategy
