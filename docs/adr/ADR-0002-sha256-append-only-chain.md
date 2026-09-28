# ADR-0002: SHA-256 append-only hash chain for tamper-evidence

## Status

Accepted

## Context

The consent registry must provide cryptographic proof that consent records have not been modified after write. This is required by:

- **GDPR Art. 7(1):** The controller must be able to demonstrate that consent was given. A tamper-evident ledger provides this demonstration.
- **ISO 27001 A.8.12:** Data integrity controls must prevent unauthorized modification. A hash chain detects any modification.
- **SOC 2 CC7.x:** System operations must be auditable. A hash chain provides an audit trail.

**Options considered:**

1. **ORM-only append-only (current state):** The `ConsentRecord.save()` raises on update. This is bypassable via `QuerySet.update()`, `bulk_create`, or raw SQL. **Rejected:** not tamper-evident.

2. **Database-level append-only:** Revoke `UPDATE`/`DELETE` grants from the application role. This prevents modification via the application, but a DBA with admin access can still modify records. **Accepted as a layer, but insufficient alone.**

3. **Append-only SHA-256 hash chain:** Each record carries a `prev_hash` (hash of the previous record) and an `entry_hash` (hash of the current record). Any modification breaks the chain. An offline verifier can detect any tampering. **Accepted.**

4. **External timestamping (RFC 3161):** Anchor the chain to an independent timestamping authority. This provides the strongest evidential weight, but adds a vendor, cost, and operational complexity. **Rejected for Phase 0** (no new vendor), but can be added later.

5. **Blockchain / distributed ledger:** Use a blockchain or distributed ledger for immutability. **Rejected:** overkill for this use case; adds significant complexity and cost.

## Decision

Implement an **append-only SHA-256 hash chain** for the consent registry.

**Key properties:**
- **SHA-256:** Cryptographically strong hash function. Collision-resistant.
- **Append-only:** Each record carries `prev_hash` (hash of the previous record) and `entry_hash` (hash of the current record). The genesis record has `prev_hash = "0" * 64`.
- **Canonical serialization:** The `entry_hash` is computed over a canonical serialization of the record:
  - Field order: alphabetical by field name
  - Encoding: UTF-8
  - Null handling: explicit `"null"` string
  - Example: `{"consent_version":"CT-marketing-v1","granted":true,"prev_hash":"abc...","purpose":"marketing","subject_id":"uuid","timestamp":"2026-09-26T12:00:00Z"}`
- **Offline verifier:** A stdlib-only Python script (`scripts/verify_chain.py`) that reads all records from the database, recomputes the hash chain, and verifies that it is consistent. The verifier can be run independently of the Django app.
- **CI integration:** The chain verifier runs on a schedule (e.g., daily) and on every deployment. If the chain is invalid, the CI job fails and an alert fires.

**Why SHA-256:**
- House pattern: `jolarca-compliance/scripts/evidence-hash.py` already uses SHA-256 for evidence integrity. Reusing the same algorithm maintains consistency.
- Widely supported: SHA-256 is supported by Python's stdlib (`hashlib`), PostgreSQL, and all major programming languages.
- Collision-resistant: No known practical collisions.

**Why not SHA-3 or BLAKE2:**
- SHA-256 is sufficient for this use case. SHA-3 and BLAKE2 are newer, but SHA-256 is well-established and widely supported.
- Consistency with the house pattern (`evidence-hash.py`).

## Consequences

**Positive:**
- Tamper-evident: any modification is detected by the chain verifier
- Cryptographic proof: provides strong evidence of immutability
- Offline verification: the verifier can be run independently, without trusting the Django app
- House pattern: consistent with `jolarca-compliance/scripts/evidence-hash.py`

**Negative:**
- Adds complexity: the chain must be computed and verified on every write
- Adds storage: each record carries two additional hashes (64 bytes each)
- Adds latency: computing the hash adds a small amount of latency to every write

**Neutral:**
- The chain is only as strong as the DB-level append-only enforcement. If a DBA can modify records, the chain will detect it, but the modification has already occurred. Mitigation: DBA actions are logged to an immutable audit log.

## Compliance mapping

| Control | How satisfied |
|---|---|
| GDPR Art. 7(1) | Hash chain provides cryptographic proof of immutability |
| ISO 27001 A.8.12 | Hash chain detects unauthorized modification |
| SOC 2 CC7.x | Hash chain provides an audit trail |

## References

- `jolarca-compliance/scripts/evidence-hash.py` — house pattern for SHA-256 evidence integrity
- `docs/architecture.md` — system context and components
- `docs/threat-model.md` — threats T1-T10 and mitigations
