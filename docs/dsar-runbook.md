# DSAR Runbook — Cross-service Data Subject Access Request procedure

## Purpose

This runbook defines the step-by-step procedure for fulfilling Data Subject Access Requests (DSARs) across all Journey of Life systems that hold personal data. It covers the full lifecycle: receive, verify identity, locate data across services, assemble response, deliver, and record — within the **30-calendar-day deadline** mandated by GDPR Art. 12(3).

**Legal basis:**

| GDPR Article | Right | Covered in this runbook |
|---|---|---|
| Art. 15 | Right of access | Section 5 — data collection and export |
| Art. 16 | Right to rectification | Section 5.4 |
| Art. 17 | Right to erasure | Section 5.5 (anonymize-don't-delete for consent ledger) |
| Art. 18 | Right to restriction of processing | Section 5.6 |
| Art. 20 | Right to data portability | Section 5.3 (machine-readable export) |
| Art. 21 | Right to object | Section 5.7 |
| Art. 12(3) | 30-day deadline | Section 3 — deadline tracking |

## Scope

### Systems holding personal data

| System | Repo / location | Personal data held | DSAR relevance |
|---|---|---|---|
| **jolarca-consent** | This repository | `subject_id` (UUID), `ip_address`, `user_agent`, consent metadata | Primary: consent ledger is system of record for consent proof (Art. 7) |
| **jolarca** (product) | `jolarca/backend/` | User accounts (email, name, password hash), profile data, marketplace listings, order history, old `users_app.ConsentRecord` table (until migration complete) | Primary: holds the bulk of personal data |
| **jolarca-legal** | `jolarca-legal/` | Legal-text publication pipeline; no personal data by design | Not applicable (no personal data stored) |
| **jolarca-compliance** | `jolarca-compliance/` | ROPA, DPIA, retention classes, policies; **hard rule: no personal data** (README.md:6-9) | Not applicable (no personal data stored) |
| **PostgreSQL backups** | Bare metal (PITR) | Full copy of all database personal data at backup time | Erasure requires backup expiry per retention policy |
| **Application logs** | GKE (Prometheus / stdout) | May contain `subject_id`, `ip_address` in structured log entries | Erasure requires log rotation / expiry |
| **Redis cache** | GKE | Non-authoritative consent-state pointers; may cache `subject_id` | Eviction on request |

### Systems NOT in scope

- `jolarca-compliance` — no personal data by hard rule
- `jolarca-legal` — no personal data by design
- `jolarca-infrastructure` — Terraform configs, no personal data
- Third-party services — none currently integrated (no analytics, no CDNs with PII)

## Roles and responsibilities

| Role | Responsibility | Who |
|---|---|---|
| **Controller** | Final authority on DSAR fulfilment; identity verification; response approval | `@JourneyOfLife` (ADR-0004) |
| **Supervisory authority** | Complaints, disputes, enforcement | VDAI (Lithuanian State Data Protection Inspectorate) |
| **Data subject** | The individual exercising their rights | Requester |

## Deadline tracking

### Statutory deadlines (Art. 12(3))

| Event | Deadline | Action |
|---|---|---|
| Request received | Day 0 | Log in DSAR register (see Section 7) |
| Identity verification | Day 0–5 | Request proof of identity if not already authenticated |
| Acknowledge receipt | Day 0–7 | Send confirmation to data subject |
| Extension notice (if needed) | Day 0–30 | Notify data subject of extension + reasons (max +2 months for complex requests) |
| Response delivered | Day 0–30 | Provide data / confirm erasure / confirm restriction |
| Supervisory authority complaint | Any time | Data subject may complain to VDAI at any point |

### Extension criteria

A request may be extended by up to 2 additional months (Art. 12(3)) only when:

1. The request is complex (e.g., spans many systems, requires reconciliation)
2. The request is numerous (e.g., data subject has made multiple related requests)
3. The data subject is informed of the extension within 30 days, with reasons

**For this system:** A cross-service DSAR spanning jolarca + jolarca-consent + backups/logs may qualify as "complex." Document the justification in the DSAR register entry.

## Procedure

### Step 1: Receive the request

**Input:** A data subject submits a request via any channel (email, in-app, verbal, letter).

**Actions:**

1. Log the request in the DSAR register (Section 7) immediately. Record:
   - Date and time of receipt (Day 0)
   - Channel of receipt
   - Requested right(s) (access, erasure, rectification, portability, restriction, objection)
   - Data subject's stated identity (email, username, or other identifier)
   - Deadline: Day 0 + 30 calendar days
2. If the request is ambiguous, clarify with the data subject within 5 business days. Do not let clarification delay the deadline — if unclear, treat as an access request (broadest scope) and narrow later.

### Step 2: Verify identity

**Before disclosing or modifying any personal data, confirm the requester's identity.**

**Actions:**

1. If the data subject is an authenticated user of the marketplace:
   - Verify via the product's existing authentication (email + password, or OAuth)
   - Record the verified `subject_id` (UUID) from the user account
2. If the data subject is not an authenticated user:
   - Request a verifiable identifier (e.g., email address associated with the account)
   - Send a confirmation link to that email address
   - Do not disclose data until identity is confirmed
3. If identity cannot be verified:
   - Inform the data subject (Art. 12(2))
   - Do not disclose or modify data
   - Record the failure in the DSAR register

### Step 3: Locate data across all systems

Using the verified `subject_id` (and any additional identifiers like email), query each in-scope system:

#### 3a. jolarca-consent (consent registry)

```
GET /api/v1/dsr/export/?subject_id=<uuid>
```

Returns all consent records (grants, withdrawals, anonymization events) for the subject. This is the authoritative consent history.

**Personal data in response:**
- `subject_id` — UUID
- `ip_address` — IP at time of consent (if not anonymized)
- `user_agent` — browser string at time of consent (if not anonymized)
- `purpose`, `consent_version`, `granted`, `timestamp`, `revoked_at` — consent metadata

#### 3b. jolarca (product database)

Query the product database for the subject's personal data:

- **User account:** email, display name, date of birth, locale, created_at
- **Profile data:** address, phone number (if provided)
- **Marketplace data:** listings created, orders placed, messages sent
- **Old consent table** (`users_app_consentrecord`): if migration (migration-plan.md) is not yet complete, this table also holds consent records

**How to query:** Use the product's admin interface or a direct database query against a read replica. Never query production directly without logging the access.

#### 3c. Redis cache

If the product caches consent state for the subject:

```
# Flush cached consent pointers for this subject
DEL consent_cache:<subject_id>
```

This is a non-authoritative cache; the canonical data is in jolarca-consent.

#### 3d. Application logs

Check structured logs for the subject's `subject_id` or `ip_address`:

- Logs are retained per the infrastructure retention policy (typically 30–90 days)
- If the data subject requests erasure and logs contain their data: logs cannot be selectively edited (integrity requirement). Instead, note in the response that log data will expire naturally per the retention schedule. This is acceptable under GDPR Recital 26 (data that "does not relate to an identified or identifiable natural person" after the retention period is not personal data).

#### 3e. PostgreSQL backups

- Backups contain a full copy of all database personal data at backup time
- Backups are retained per the PITR policy (typically 7–30 days)
- Selective erasure from backups is technically infeasible without breaking PITR
- Note in the response that backup data will expire naturally per the backup retention schedule
- This is acceptable: backups are not "processed" in the GDPR sense (Recital 26) — they are disaster-recovery copies that are not accessed, queried, or used for any purpose other than restoration

### Step 4: Assemble the response

#### 4a. Access request (Art. 15)

Compile a machine-readable JSON export containing:

1. **Consent registry data** — output of the DSR export endpoint (Section 3a)
2. **Product account data** — user profile, marketplace data (Section 3b)
3. **Processing purposes** — for each data category, state the purpose and legal basis
4. **Retention periods** — reference `jolarca-compliance/retention/matrix.yaml`
5. **Recipients** — list any third parties who received the data (currently: none)
6. **Rights notice** — inform the data subject of their rights to rectification, erasure, restriction, objection, and complaint to VDAI

**Format:** JSON (machine-readable, per Art. 20 portability requirement). Also provide a human-readable summary.

#### 4b. Portability request (Art. 20)

The JSON export from 4a satisfies the portability requirement. Ensure:

- Data is in a "structured, commonly used, machine-readable format" (JSON)
- Data is transmitted directly to the data subject or, where technically feasible, to another controller designated by the data subject

#### 4c. Rectification request (Art. 16)

1. Identify the inaccurate data in the relevant system(s)
2. **jolarca-consent:** Consent records are append-only and cannot be modified. If a consent record contains inaccurate data (e.g., wrong `ip_address`), the correct approach is:
   - Append a new record with the corrected data (if the inaccuracy relates to consent metadata)
   - If the inaccuracy relates to an already-anonymized record, no action is needed (the personal data is already gone)
3. **jolarca (product):** Update the user account / profile data directly
4. Inform the data subject of the correction

#### 4d. Erasure request (Art. 17)

**This is the most complex request type due to the append-only consent ledger.**

1. **jolarca (product):**
   - Delete or anonymize the user account per the product's erasure procedure
   - Delete or anonymize marketplace listings, orders, messages (or anonymize if retention is legally required — e.g., tax records)
   - Document what was erased and what was retained (with legal basis for retention)

2. **jolarca-consent (consent registry):**
   - **Do NOT delete consent records.** Art. 7(1) requires retaining proof of consent. ADR-0003 resolves this via anonymize-don't-delete.
   - Execute the anonymization procedure:
     - `POST /api/v1/consent-records/<id>/anonymize` for each consent record belonging to the subject
     - This replaces `subject_id` with an unlinkable UUID, clears `ip_address` and `user_agent`, sets `anonymized_at`
     - The hash chain is preserved (anonymization event appended, original hashes unchanged)
   - Verify the chain after anonymization: `python scripts/verify_chain.py`
   - Inform the data subject that their personal data has been erased from the consent ledger, but the fact that consent was given/withdrawn is retained (as required by law)

3. **Redis cache:**
   - Evict any cached data for the subject (Section 3c)

4. **Logs and backups:**
   - Note that log data and backup data will expire naturally per retention schedules
   - This is acceptable under GDPR Recital 26

#### 4e. Restriction request (Art. 18)

1. Mark the data subject's account in the product as "processing restricted"
2. In jolarca-consent: no action needed (the registry only appends; it does not "process" in any other sense)
3. Inform the data subject that processing has been restricted

#### 4f. Objection request (Art. 21)

1. Evaluate whether the controller has "compelling legitimate grounds" to continue processing (Art. 21(1))
2. If no compelling grounds: treat as an erasure request (Section 4d)
3. If compelling grounds exist: document the justification in the DSAR register and inform the data subject

### Step 5: Deliver the response

1. Send the response to the data subject via a secure channel (encrypted email, or in-app secure message)
2. Record the delivery date in the DSAR register
3. Confirm the response was within the 30-day deadline

### Step 6: Record and close

1. Update the DSAR register with:
   - Systems queried and data found
   - Actions taken (erased, anonymized, rectified, restricted)
   - Response delivered (date, channel)
   - Any extensions granted
2. Close the DSAR entry

## Escalation

| Condition | Action |
|---|---|
| Identity cannot be verified after 10 days | Close the request; inform the data subject |
| Request is manifestly unfounded or excessive | May refuse (Art. 12(4)); document justification; inform data subject of right to complain to VDAI |
| Deadline at risk (>25 days elapsed) | Escalate to controller immediately; consider extension notice |
| Data subject complains to VDAI | Cooperate fully with the supervisory authority (Art. 31); provide all DSAR register entries |
| Cross-border request (data subject in different EU state) | No change in procedure; VDAI is the lead authority for the controller's establishment |

## DSAR register

Maintain a register of all DSARs. This register is itself a compliance artifact and must be retained.

| Field | Description |
|---|---|
| `dsar_id` | Unique identifier (e.g., `DSAR-2026-001`) |
| `received_at` | Date and time of receipt (Day 0) |
| `channel` | How the request was received (email, in-app, letter, verbal) |
| `right_requested` | Art. 15 / 16 / 17 / 18 / 20 / 21 |
| `subject_identifier` | Email or username provided by the requester |
| `subject_uuid` | Verified `subject_id` (UUID) from the user account |
| `identity_verified` | Boolean — was identity confirmed? |
| `deadline` | Day 0 + 30 calendar days |
| `extended` | Boolean — was the deadline extended? |
| `extension_reason` | If extended, why |
| `systems_queried` | List of systems queried (jolarca-consent, jolarca, redis, logs) |
| `data_found` | Summary of data found in each system |
| `actions_taken` | What was done (erased, anonymized, rectified, restricted, exported) |
| `response_delivered_at` | Date and time the response was sent |
| `closed_at` | Date the DSAR was closed |
| `notes` | Any additional notes |

**Storage:** The DSAR register is maintained in `jolarca-compliance` (no personal data in the register itself — only metadata about the request process). The register does not contain the data subject's personal data; it references the `dsar_id` and outcome.

## Consent-registry-specific notes

### Why consent records cannot be deleted

The consent ledger is append-only by design (ADR-0002, ADR-0003). This is not a technical limitation — it is a compliance control. Deleting consent records would violate Art. 7(1) (demonstrability of consent) and break the SHA-256 hash chain that provides tamper-evidence.

### Anonymize-don't-delete (ADR-0003)

When a data subject requests erasure of their consent data:

1. The `subject_id` (UUID) is replaced with a new random UUID that cannot be linked back to the data subject
2. `ip_address` and `user_agent` are cleared
3. `purpose`, `consent_version`, `timestamp`, `granted` are retained (these are not personal data after anonymization)
4. An anonymization event is appended to the hash chain
5. The chain remains valid and verifiable

After anonymization, the consent record is no longer personal data (Recital 26: "information which does not relate to an identified or identifiable natural person"). The Art. 17 obligation is satisfied.

### What to tell the data subject

> "Your personal data has been erased from our consent registry. The fact that you gave (or withdrew) consent is retained for legal compliance (GDPR Art. 7(1)), but it can no longer be linked to you. This is verified by our tamper-evident hash chain, which you can independently verify."

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-28 | 1.0 | Agent | Initial cross-service DSAR runbook |
