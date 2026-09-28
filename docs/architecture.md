# Architecture — jolarca-consent

## Purpose

`jolarca-consent` is the **independent consent registry of record** for the Journey of Life marketplace. It extracts `ConsentRecord` out of the marketplace application (`jolarca/backend/apps/users_app/models.py:71-91`) into a separately owned, tamper-evident service whose entries cannot be modified by the party that needs consent.

**Why a separate service:** The marketplace application currently owns both the consent UX (the party that needs consent) and the consent record (the proof of consent). Whoever controls the app database controls the evidence. That defeats **GDPR Art. 7(1)** demonstrability, **ISO 27001 A.8.12** integrity, and **SOC 2 CC7.x**, because the control and the thing it constrains share an owner.

## System context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              jolarca-consent                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  consent_registry (Django app)                                       │  │
│  │  - ConsentRecord model (append-only, hash-chained)                   │  │
│  │  - API: grant, withdraw, query, DSR export                           │  │
│  │  - AuthN: API key in Vault, HMAC-signed requests                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  consent_integrity (Django app)                                      │  │
│  │  - Hash chain: SHA-256 prev-hash chain                               │  │
│  │  - Canonical serialization (alphabetical, UTF-8, null="null")        │  │
│  │  - Offline verifier (stdlib-only script)                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  PostgreSQL (append-only ledger)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
         ▲                                    ▲
         │ append/query                       │ cross-check
         │                                    │
┌────────┴─────────┐                  ┌───────┴────────┐
│  jolarca (product)│                  │  jolarca-legal │
│  - Consent UX     │                  │  - Legal-text  │
│  - Calls API      │                  │    publication │
│  - Caches pointer │                  │    pipeline    │
└──────────────────┘                  └────────────────┘
         │
         │ reads texts
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         jolarca-compliance                                  │
│  - Consent texts (lawful-basis/consent-text/<lang>/CT-*.md)                 │
│  - Version ledger (lawful-basis/consent-versions.md)                        │
│  - ROPA, DPIA, retention classes, policies                                  │
│  - NO personal data (hard rule: README.md:6-9)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### consent_registry

The Django app that owns the `ConsentRecord` schema and the API.

**Responsibilities:**
- Accept consent grant/withdrawal requests from authenticated callers
- Query effective consent state for a subject
- Query full history for a subject (DSR Art. 15/20)
- Enforce schema-level validation (purpose taxonomy, version format)
- Delegate to `consent_integrity` for hash-chain operations

**Key design decisions:**
- **Append-only, enforced in depth.** ORM guard (`save()` raises on update) *and* DB-level protection (revoked `UPDATE`/`DELETE` grants for the application role). ORM-only is the defect being fixed.
- **Withdrawal ≠ deletion.** Art. 7(1) requires proving consent was given; Art. 17 grants erasure. Resolve via **anonymize-don't-delete** (ADR-0003): anonymize the subject identifier, retain purpose, version, timestamp, and the fact of grant/withdrawal.
- **Version mapping is total.** Every purpose the product can request must have an approved `CT-<purpose>-v<N>` text in `jolarca-compliance/lawful-basis/consent-text/`. The registry rejects unknown versions at the schema level.

### consent_integrity

The Django app that owns the hash chain and verification logic.

**Responsibilities:**
- Compute `entry_hash` for each consent record (SHA-256 over canonical serialization)
- Maintain `prev_hash` chain (genesis entry has `prev_hash = "0" * 64`)
- Provide stdlib-only offline verifier (`scripts/verify_chain.py`)
- Expose chain verification as an API endpoint (for CI and on-demand checks)

**Canonical serialization (ADR-0002):**
- Field order: alphabetical by field name
- Encoding: UTF-8
- Null handling: explicit `"null"` string
- Example: `{"consent_version":"CT-marketing-v1","granted":true,"prev_hash":"abc...","purpose":"marketing","subject_id":"uuid","timestamp":"2026-09-26T12:00:00Z"}`

### PostgreSQL

The database storing the append-only ledger.

**Key constraints:**
- Application role has `INSERT` only; `UPDATE`/`DELETE` revoked
- Separate admin role for migrations (used only during deployments, not at runtime)
- Regular backups with point-in-time recovery (PITR)
- Encryption at rest (pgcrypto or infrastructure-level disk encryption)

## Data flow

### Consent grant

```
1. Product receives user consent action (UI)
2. Product authenticates to registry (API key in Vault, HMAC-signed request)
3. Product calls POST /api/v1/consent-records/
   {
     "subject_id": "<user-uuid>",
     "purpose": "marketing",
     "consent_version": "CT-marketing-v1",
     "granted": true,
     "ip_address": "1.2.3.4",
     "user_agent": "Mozilla/5.0...",
     "timestamp": "2026-09-26T12:00:00Z"
   }
4. Registry validates:
   - subject_id is a valid UUID
   - purpose is in the approved taxonomy
   - consent_version matches an approved text in jolarca-compliance
   - timestamp is within acceptable skew (±5 minutes)
5. Registry computes entry_hash (SHA-256 over canonical serialization)
6. Registry inserts record with prev_hash = hash of most recent record
7. Registry returns 201 Created with the record ID and entry_hash
8. Product caches the record ID (non-authoritative pointer)
```

### Consent query

```
1. Product calls GET /api/v1/consent-records/?subject_id=<uuid>&purpose=marketing
2. Registry authenticates caller
3. Registry queries the ledger for the most recent record matching the filter
4. Registry returns the record (or 404 if none)
5. Product uses the record to enforce consent
```

### Consent withdrawal

```
1. Product receives user withdrawal action (UI)
2. Product calls POST /api/v1/consent-records/
   {
     "subject_id": "<user-uuid>",
     "purpose": "marketing",
     "consent_version": "CT-marketing-v1",
     "granted": false,
     "revoked_at": "2026-09-26T13:00:00Z",
     ...
   }
3. Registry validates and inserts a NEW record with granted=false
4. The original grant record is NOT modified or deleted
5. Effective consent state = most recent record for (subject_id, purpose)
```

### DSR export (Art. 15/20)

```
1. DPO or automated system calls GET /api/v1/dsr/export?subject_id=<uuid>
2. Registry authenticates caller (elevated privilege required)
3. Registry queries all records for the subject
4. Registry returns a JSON export of the consent history
5. Export is logged as a DSR event
```

### Chain verification

```
1. CI job or operator calls GET /api/v1/integrity/verify-chain
2. Registry reads all records in insertion order
3. For each record, recomputes entry_hash and checks:
   - entry_hash matches stored value
   - prev_hash matches the entry_hash of the previous record
4. Registry returns 200 OK if chain is valid, 409 Conflict if any mismatch
5. Offline verifier (scripts/verify_chain.py) performs the same check directly against the DB
```

## Trust model

**What the registry trusts:**
- The product to record consent truthfully at write time. The registry cannot verify the truth of "user X clicked accept" — that is the product's responsibility.
- Vault to manage API keys securely.
- PostgreSQL to enforce DB-level append-only constraints.

**What the registry does NOT trust:**
- The product to preserve records after write. Once written, the registry guarantees immutability via the hash chain and DB constraints.
- The product to report consent state accurately. The registry is the system of record; the product may cache, but the cache is non-authoritative.

**What the registry guarantees:**
- Immutability after write. No one (including the product, the registry operators, or a DBA with read access) can modify or delete a finalized record without breaking the chain.
- Verifiability. Anyone with read access to the DB can run the offline verifier and confirm the chain is intact.
- Non-repudiation. The hash chain provides cryptographic proof that a record existed at a given time with given contents.

**What the registry does NOT guarantee:**
- Truth at write time. The registry cannot verify that the product's claim "user X consented" is true. That is the product's responsibility, enforced by the product's own controls (UI, audit logs, etc.).

## Deployment

**Infrastructure:** Bare metal + GKE (per `jolarca-infrastructure/README.md`). The consent registry runs as a Django service in GKE, with PostgreSQL on bare metal.

**Secrets:** API keys stored in Vault, injected at runtime via environment variables. No secrets in code, env files, or chat (per `jolarca-compliance/policies/03-access-control.md:19`).

**Networking:** WireGuard mesh between bare metal and GKE (per `jolarca-infrastructure/README.md:19`). The registry is accessible only from the marketplace network, not from the public internet.

**Monitoring:** Prometheus metrics for API latency, error rates, chain verification status. Alerts on chain verification failure (highest severity).

## Compliance mapping

| Control | How satisfied |
|---|---|
| GDPR Art. 7(1) — demonstrability of consent | Registry is system of record; hash chain provides cryptographic proof |
| GDPR Art. 17 — right to erasure | Anonymize-don't-delete (ADR-0003); subject identifier anonymized, consent fact retained |
| ISO 27001 A.8.12 — data integrity | Hash chain + DB-level append-only + offline verifier |
| SOC 2 CC7.x — system operations | Separation of duties: product needs consent but does not own the proof |
| ISO 27001 A.8.9 — configuration management | House tooling standards (ruff, mypy, pre-commit, Makefile) |
| SOC 2 CC6.1 — logical access | API key in Vault, HMAC-signed requests, least privilege |

## Open questions

None at this time. All Phase 0 decisions are resolved.

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-26 | 1.0 | Agent | Initial architecture for Phase 0 |
