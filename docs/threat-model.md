# Threat Model — jolarca-consent

## Scope

This threat model enumerates the ways the append-only guarantee of the consent registry could be bypassed, and the mitigations that prevent each. The append-only guarantee is the point of the entire project; any bypass that is not detected and prevented is a compliance failure.

**Assets:**
- Consent records (personal data: subject_id, purpose, consent_version, granted, ip_address, user_agent, timestamp)
- Hash chain (cryptographic proof of immutability)
- API keys (authentication credentials)

**Threat actors:**
- **External attacker:** Compromises the product, the registry, or the network
- **Malicious insider (product team):** Attempts to modify consent records to cover up unauthorized processing
- **Malicious insider (registry operations):** Attempts to modify records or the chain
- **DBA with read/write access:** Attempts to modify records directly in the database

**Out of scope:**
- Truth at write time (the registry cannot verify that the product's claim is true)
- Availability (denial-of-service attacks; handled by infrastructure-level controls)
- Physical security (handled by bare-metal provider)

## Threats and mitigations

### T1: Product modifies a record after write via the API

**Scenario:** The product calls the API to write a consent record, then later calls the API again to modify it (e.g., change `granted` from true to false without a withdrawal record).

**Mitigation:**
- The API does not expose `PUT` or `PATCH` endpoints. Only `POST` (append) and `GET` (query) are available.
- The `ConsentRecord` model's `save()` method raises `ValueError` if `_state.adding` is false (append-only at ORM level).
- **DB-level enforcement:** The application role has `INSERT` only; `UPDATE` is revoked. Even if the ORM guard is bypassed, the DB rejects the update.
- **Hash chain:** Any modification breaks the chain. The offline verifier detects it.

**Residual risk:** Low. Requires compromising both the application code and the DB role grants, and the chain would still detect the modification.

**Verification (Phase 3 gate):** Test that `PUT /api/v1/consent-records/<id>/` returns 405 Method Not Allowed. Test that `ConsentRecord.objects.filter(...).update(...)` raises. Test that the chain verifier detects a manually modified record.

### T2: Product deletes a record via the API

**Scenario:** The product calls the API to delete a consent record (e.g., to erase evidence of consent).

**Mitigation:**
- The API does not expose `DELETE` endpoints.
- The `ConsentRecord` model's `delete()` method raises `ValueError` (append-only at ORM level).
- **DB-level enforcement:** The application role has no `DELETE` privilege.
- **Hash chain:** Any deletion breaks the chain. The offline verifier detects a gap in the `prev_hash` sequence.

**Residual risk:** Low. Same as T1.

**Verification (Phase 3 gate):** Test that `DELETE /api/v1/consent-records/<id>/` returns 405. Test that `ConsentRecord.objects.filter(...).delete()` raises. Test that the chain verifier detects a missing record.

### T3: DBA modifies a record directly in the database

**Scenario:** A DBA with read/write access to the production database updates a consent record directly (e.g., `UPDATE consent_record SET granted = false WHERE id = '...'`).

**Mitigation:**
- **DB-level enforcement:** The application role (used by the Django app at runtime) has `INSERT` only. The DBA uses a separate admin role, but all admin actions are logged to an immutable audit log (per `jolarca-compliance/policies/03-access-control.md:20`: "Production access is break-glass or ticketed; all sessions logged").
- **Hash chain:** Any modification breaks the chain. The offline verifier (run on a schedule by CI) detects it.
- **Alerting:** Chain verification failure triggers a highest-severity alert.

**Residual risk:** Medium. A DBA could modify a record and then modify the audit log to cover their tracks. Mitigation: audit logs are shipped to an immutable external sink (per `jolarca/backend/apps/compliance_app/models.py:14`).

**Verification (Phase 3 gate):** Test that the chain verifier detects a record modified via direct SQL. Test that the alert fires.

### T4: DBA deletes a record directly in the database

**Scenario:** A DBA deletes a consent record directly (e.g., `DELETE FROM consent_record WHERE id = '...'`).

**Mitigation:**
- **DB-level enforcement:** Same as T3.
- **Hash chain:** Any deletion breaks the chain. The offline verifier detects a gap in the `prev_hash` sequence.
- **Alerting:** Same as T3.

**Residual risk:** Medium. Same as T3.

**Verification (Phase 3 gate):** Test that the chain verifier detects a deleted record. Test that the alert fires.

### T5: Attacker forges a new chain from a modified genesis

**Scenario:** An attacker modifies the genesis record (the first record in the chain) and then re-computes all subsequent hashes to create a new, consistent chain.

**Mitigation:**
- **DB-level enforcement:** The attacker would need to modify all records in the chain, which requires `UPDATE` on all rows. The application role has no `UPDATE`. The admin role is logged.
- **External anchoring (future):** The chain could be anchored to an external timestamping authority (RFC 3161) to provide an independent proof of the chain's state at a given time. This is out of scope for Phase 0 (no new vendor), but could be added later.
- **Monitoring:** The chain verifier runs on a schedule. If the attacker modifies the chain between verifications, the gap is detected at the next verification.

**Residual risk:** Medium. Without external anchoring, a sufficiently privileged attacker could forge a chain. Mitigation: the attack requires modifying all records, which is logged and detectable.

**Verification (Phase 3 gate):** Test that the chain verifier detects a forged genesis. Test that the alert fires.

### T6: Attacker truncates the ledger (deletes the tail)

**Scenario:** An attacker deletes the most recent records in the chain (e.g., to erase evidence of recent consent).

**Mitigation:**
- **DB-level enforcement:** Same as T3/T4.
- **Hash chain:** Truncation breaks the chain. The offline verifier detects that the most recent `prev_hash` does not match any record's `entry_hash`.
- **Monitoring:** The chain verifier detects truncation.

**Residual risk:** Low. Truncation is a special case of deletion, which the chain detects.

**Verification (Phase 3 gate):** Test that the chain verifier detects a truncated ledger.

### T7: Attacker reorders records

**Scenario:** An attacker reorders records in the database (e.g., swaps the order of two records to change the effective consent state).

**Mitigation:**
- **Hash chain:** Reordering breaks the chain. Each record's `prev_hash` points to the previous record's `entry_hash`. If the order changes, the chain is inconsistent.
- **Insertion order:** The chain is built in insertion order (by `created_at` timestamp). Reordering would require modifying `created_at`, which is a modification detected by the chain.

**Residual risk:** Low. Reordering is detected by the chain.

**Verification (Phase 3 gate):** Test that the chain verifier detects reordered records.

### T8: Attacker compromises an API key

**Scenario:** An attacker steals an API key and uses it to write fraudulent consent records.

**Mitigation:**
- **Vault-managed keys:** API keys are stored in Vault, not in code or env files.
- **Rotation:** API keys are rotated per policy (per `jolarca-compliance/policies/03-access-control.md:21`: "Quarterly access review").
- **HMAC signing:** Requests are HMAC-signed, so the attacker needs the key, not just the key ID.
- **Audit log:** All API calls are logged. Fraudulent writes can be detected by anomaly detection (e.g., sudden spike in consent records for a single subject).
- **Truth at write time:** The registry cannot prevent fraudulent writes, but the product's own controls (UI, audit logs) should detect them.

**Residual risk:** Medium. The registry cannot verify truth at write time. Mitigation: audit logs, anomaly detection, and the product's own controls.

**Verification (Phase 3 gate):** Not applicable (this is a product-side control, not a registry control).

### T9: Attacker modifies the chain verifier

**Scenario:** An attacker modifies the chain verifier code to skip certain checks, allowing a modified chain to pass verification.

**Mitigation:**
- **Code review:** All changes to the verifier require code review (per `jolarca-compliance/policies/08-secure-development.md`).
- **CI/CD:** The verifier is tested by the adversarial suite (Phase 3 gate). If the verifier is modified to skip checks, the adversarial tests fail.
- **Offline verifier:** The offline verifier (`scripts/verify_chain.py`) is a separate, stdlib-only script. It can be run independently of the Django app. If the Django app's verifier is compromised, the offline verifier still detects the modification.

**Residual risk:** Low. Requires compromising both the Django app and the offline verifier, and bypassing CI.

**Verification (Phase 3 gate):** Test that the adversarial suite fails if the verifier is modified to skip checks.

### T10: Attacker modifies the canonical serialization

**Scenario:** An attacker modifies the canonical serialization logic (the code that computes `entry_hash`) to produce different hashes for the same data, allowing a modified record to pass verification.

**Mitigation:**
- **Same as T9.** The canonical serialization is tested by the adversarial suite. If it is modified, the adversarial tests fail.
- **Offline verifier:** The offline verifier implements the same canonical serialization. If the Django app's serialization is compromised, the offline verifier still detects the modification.

**Residual risk:** Low. Same as T9.

**Verification (Phase 3 gate):** Test that the adversarial suite fails if the canonical serialization is modified.

## Summary

| Threat | Likelihood | Impact | Residual risk | Mitigation strength |
|---|---|---|---|---|
| T1: API modification | Low | High | Low | Strong (API + ORM + DB + chain) |
| T2: API deletion | Low | High | Low | Strong (API + ORM + DB + chain) |
| T3: DBA modification | Medium | High | Medium | Moderate (DB + chain + audit log) |
| T4: DBA deletion | Medium | High | Medium | Moderate (DB + chain + audit log) |
| T5: Forged genesis | Low | Critical | Medium | Moderate (DB + chain; external anchoring future) |
| T6: Truncation | Low | High | Low | Strong (DB + chain) |
| T7: Reordering | Low | High | Low | Strong (chain) |
| T8: API key compromise | Medium | Medium | Medium | Moderate (Vault + rotation + audit) |
| T9: Verifier modification | Low | Critical | Low | Strong (code review + CI + offline verifier) |
| T10: Serialization modification | Low | Critical | Low | Strong (code review + CI + offline verifier) |

## Open questions

- **External anchoring (T5):** Should we add RFC 3161 timestamping to provide an independent proof of the chain's state? This is out of scope for Phase 0 (no new vendor), but should be revisited after Phase 4.

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-26 | 1.0 | Agent | Initial threat model for Phase 0 |
