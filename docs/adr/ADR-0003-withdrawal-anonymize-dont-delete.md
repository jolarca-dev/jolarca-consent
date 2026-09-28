# ADR-0003: Withdrawal via anonymize-don't-delete (Art. 7 vs Art. 17)

## Status

Accepted

## Context

**The conflict:**

- **GDPR Art. 7(1)** requires the controller to demonstrate that consent was given. This means the consent record must be retained as proof.
- **GDPR Art. 17** (right to erasure) gives the data subject the right to have their personal data erased.

If a user withdraws consent and requests erasure, we have two conflicting obligations:
- Retain the consent record (Art. 7(1))
- Erase the personal data (Art. 17)

**Current state:**

The current `ConsentRecord` model has `user = models.ForeignKey(User, on_delete=models.PROTECT)` (`jolarca/backend/apps/users_app/models.py:75`). This means:
- If a user is deleted, the consent record blocks the deletion (PROTECT)
- The consent record is retained, but the user's personal data is also retained (via the FK)
- This is a partial solution: it retains the proof, but does not erase the personal data

**Options considered:**

1. **Delete the consent record on erasure:** Erase the consent record when the user requests erasure. **Rejected:** violates Art. 7(1) (cannot demonstrate consent was given).

2. **Retain the consent record with personal data:** Keep the consent record (including the subject_id) even after erasure. **Rejected:** violates Art. 17 (personal data not erased).

3. **Anonymize-don't-delete (house doctrine):** Anonymize the subject identifier in the consent record, but retain the purpose, version, timestamp, and the fact of grant/withdrawal. This satisfies both Art. 7(1) (proof retained) and Art. 17 (personal data erased). **Accepted.**

**House doctrine:**

`jolarca-compliance` already has a doctrine of **anonymize-don't-delete** (`docs/adr/ADR-0001-anonymize-dont-delete.md`). This ADR extends that doctrine to the consent registry.

## Decision

When a user withdraws consent and requests erasure:

1. **Anonymize the subject identifier:** Replace the `subject_id` (UUID) with a random, unlinkable value (e.g., a new UUID that cannot be traced back to the user).
2. **Retain the consent record:** Keep the purpose, consent_version, timestamp, granted/withdrawn status, and the anonymized subject_id.
3. **Log the anonymization:** Record the anonymization event in an audit log (but not the original subject_id).

**Implementation:**

- Add an `anonymized_at` field to the `ConsentRecord` model. When set, the record has been anonymized.
- Add an API endpoint `POST /api/v1/consent-records/<id>/anonymize` that:
  - Appends an "anonymization event" to the hash chain (a new record with `action="anonymize"`, referencing the original record ID)
  - Replaces `subject_id` with a new random UUID in the DB
  - Sets `anonymized_at` to the current timestamp
  - Clears `ip_address` and `user_agent` (also personal data)
  - Retains `purpose`, `consent_version`, `timestamp`, `granted`, `revoked_at`
- The anonymization is irreversible: once anonymized, the record cannot be linked back to the user.
- **The hash chain is NOT modified.** The original consent record retains its original `entry_hash`. The anonymization event is appended to the chain, referencing the original record. The chain verifier, when it encounters an anonymized record, checks that there's a corresponding anonymization event in the chain. This preserves the append-only guarantee while allowing anonymization.

**Retention:**

- Anonymized consent records are retained indefinitely (or per the retention class `RC-MARKETING-CONSENT` in `jolarca-compliance/retention/matrix.yaml`).
- The retention period is `[COUNSEL-TO-CONFIRM]` for non-marketing consent purposes.

## Consequences

**Positive:**
- Satisfies both Art. 7(1) (proof retained) and Art. 17 (personal data erased)
- Consistent with house doctrine (anonymize-don't-delete)
- Provides a clear, auditable process for withdrawal + erasure

**Negative:**
- Adds complexity: the anonymization process must be implemented and tested
- Adds storage: anonymized records are retained indefinitely
- The chain verifier must be aware of anonymization events and handle them appropriately

**Neutral:**
- The anonymized record can no longer be used to query consent state for the user (the subject_id is gone). This is intentional: the user has withdrawn consent and requested erasure.
- The anonymized record can still be used for aggregate analytics (e.g., "how many users withdrew consent for marketing?").

## Compliance mapping

| Control | How satisfied |
|---|---|
| GDPR Art. 7(1) | Proof of consent retained (anonymized) |
| GDPR Art. 17 | Personal data erased (subject_id, ip_address, user_agent) |
| ISO 27001 A.8.12 | Anonymization is logged and auditable |

## References

- `jolarca-compliance/docs/adr/ADR-0001-anonymize-dont-delete.md` — house doctrine
- `jolarca/backend/apps/users_app/models.py:75` — current `on_delete=PROTECT`
- `jolarca-compliance/retention/matrix.yaml:113-123` — `RC-MARKETING-CONSENT` retention class
- `docs/architecture.md` — data flow for consent withdrawal
- `docs/migration-plan.md` — migration strategy for existing records
