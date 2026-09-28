# Migration Plan — jolarca-consent

## Purpose

This plan describes how to extract `ConsentRecord` from the marketplace application (`jolarca/backend/apps/users_app/models.py:71-91`) into the independent consent registry (`jolarca-consent`), with rollback at each step.

**Why a phased cutover:** Consent records are personal data and compliance evidence. A failed migration could result in data loss, broken consent enforcement, or compliance violations. Each step must be reversible until the next step is verified.

## Pre-requisites

- [ ] Phase 1 complete: `jolarca-consent` repository scaffolded with governance files
- [ ] Phase 2 complete: `ConsentRecord` schema and API contract implemented in `jolarca-consent`
- [ ] Phase 3 complete: Hash chain and offline verifier implemented and tested
- [ ] API keys provisioned in Vault for `jolarca` and `jolarca-legal`
- [ ] Database role created with `INSERT`-only privileges
- [ ] Monitoring and alerting configured for chain verification failures
- [ ] DPO and compliance lead have reviewed and approved the migration plan

## Step 1: Dual-write (product writes to both old and new)

**What:** Modify the product (`jolarca`) to write consent records to both the old `users_app.ConsentRecord` table and the new `jolarca-consent` registry.

**How:**
1. Deploy `jolarca-consent` to production (read-only mode; no traffic yet)
2. Modify `jolarca/backend/apps/users_app/services.py` to call the `jolarca-consent` API after writing to the local table
3. If the API call fails, log the error but do not fail the request (the old table is still authoritative)
4. Deploy the modified product

**Verification:**
- Monitor logs for API call failures
- Compare record counts between old table and new registry (should match within a small lag)
- Run the chain verifier on the new registry (should pass)

**Rollback:**
- Revert the product deployment to the version without dual-write
- The old table remains authoritative; no data loss

**Risk:** Low. The old table is still authoritative; the new registry is a shadow copy.

## Step 2: Backfill (migrate existing records)

**What:** Migrate all existing `ConsentRecord` rows from the old table to the new registry.

**How:**
1. Run a one-time migration script (`scripts/migrate_consent_records.py`) that:
   - Reads all records from `users_app.ConsentRecord` in insertion order
   - For each record, calls the `jolarca-consent` API to create a corresponding record
   - Computes the hash chain as records are inserted
2. The migration script is idempotent: if a record already exists in the new registry (by `subject_id`, `purpose`, `timestamp`), it is skipped
3. The migration script logs every record it processes, including errors

**Verification:**
- Compare record counts between old table and new registry (should match exactly)
- Run the chain verifier on the new registry (should pass)
- Spot-check a sample of records: compare fields between old and new

**Rollback:**
- Delete all migrated records from the new registry (or mark them as "migrated" and ignore them)
- The old table remains authoritative; no data loss

**Risk:** Medium. The migration could fail partway through, leaving the new registry in an inconsistent state. Mitigation: the migration script is idempotent and can be re-run.

**Known issue:** The old `consent_version` field is `max_length=16`, but the house naming convention `CT-<purpose>-v<N>` yields values up to 18 chars (e.g., `CT-transactions-v1`). The migration script must:
- Check if any existing records have truncated `consent_version` values
- If so, flag them for manual review (cannot automatically recover the original value)
- Do not migrate truncated records until the correct value is confirmed

## Step 3: Verify (confirm new registry is consistent)

**What:** Verify that the new registry is a faithful copy of the old table, and that the hash chain is intact.

**How:**
1. Run the chain verifier on the new registry
2. Compare record counts between old table and new registry
3. Spot-check a sample of records: compare fields between old and new
4. Run a test query against the new registry: query effective consent state for a sample of users, compare with the old table

**Verification:**
- Chain verifier passes
- Record counts match
- Spot-check passes
- Query results match

**Rollback:**
- No rollback needed; this is a verification step, not a change

**Risk:** Low. This is a read-only verification step.

## Step 4: Read-cut (product reads from new registry)

**What:** Modify the product to read consent state from the new registry instead of the old table.

**How:**
1. Modify `jolarca/backend/apps/users_app/services.py` to call the `jolarca-consent` API for consent queries
2. If the API call fails, fall back to the old table (temporary safety net)
3. Deploy the modified product

**Verification:**
- Monitor logs for API call failures and fallbacks
- Compare consent enforcement decisions between old and new (should match)
- Run the chain verifier on the new registry (should pass)

**Rollback:**
- Revert the product deployment to the version that reads from the old table
- The old table remains authoritative; no data loss

**Risk:** Medium. If the new registry is unavailable, the product falls back to the old table. If the new registry returns incorrect data, consent enforcement could be wrong. Mitigation: the fallback to the old table provides a safety net.

## Step 5: Write-cut (product writes only to new registry)

**What:** Modify the product to write consent records only to the new registry, not to the old table.

**How:**
1. Modify `jolarca/backend/apps/users_app/services.py` to remove the dual-write to the old table
2. Deploy the modified product

**Verification:**
- Monitor logs for API call failures
- Verify that new consent records appear in the new registry but not the old table
- Run the chain verifier on the new registry (should pass)

**Rollback:**
- Revert the product deployment to the version that dual-writes
- The old table is no longer being written to, but the data is still there

**Risk:** Medium. If the new registry is unavailable, consent writes fail. Mitigation: the product should retry with exponential backoff, and alert if writes fail.

## Step 6: Decommission (remove old table)

**What:** Remove the old `users_app.ConsentRecord` table and related code.

**How:**
1. Wait for a cooling-off period (e.g., 30 days) to ensure no issues arise from the write-cut
2. Remove the `ConsentRecord` and `ConsentPurpose` models from `jolarca/backend/apps/users_app/models.py`
3. Remove the related migrations (or mark them as no-ops)
4. Drop the `users_app_consentrecord` table from the database
5. Update all documentation that references the old table

**Verification:**
- No code references to `ConsentRecord` in the product
- No database table `users_app_consentrecord`
- All documentation updated

**Rollback:**
- Not reversible. This is why the cooling-off period is important.

**Risk:** Low (after cooling-off period). The old table is no longer needed.

## Cross-repo changes

The migration plan requires changes to multiple repositories. These are enumerated in the kickoff prompt (§7) and should be delivered as separate PRs:

- `jolarca-legal`: Repoint `cross-check-consent.py` to the new registry API
- `jolarca-compliance`: Update `lawful-basis/README.md`, `docs/architecture.md`, `docs/retention-schedule.md`, `retention/matrix.yaml`, `ropa/master-register.csv`, `dpia/001-identity-and-consent/README.md`, `legal/cookie-policy/banner-spec.md`, `scripts/evidence-hash.py`, `lawful-basis/consent-versions.md`
- `jolarca`: Deprecate `ConsentRecord` and `ConsentPurpose`, update all consumers and docs

## Timeline

| Step | Duration | Dependencies |
|---|---|---|
| Step 1: Dual-write | 1 day | Phase 3 complete |
| Step 2: Backfill | 1-2 days (depending on data volume) | Step 1 verified |
| Step 3: Verify | 1 day | Step 2 complete |
| Step 4: Read-cut | 1 day | Step 3 verified |
| Step 5: Write-cut | 1 day | Step 4 verified (7-day observation) |
| Step 6: Decommission | 1 day | Step 5 verified (30-day cooling-off) |
| Cross-repo changes | 2-3 days (parallel with steps 4-5) | Phase 4 complete |

**Total:** ~7-10 days, plus 30-day cooling-off period before decommission.

## Open questions

None at this time. All migration decisions are resolved.

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-26 | 1.0 | Agent | Initial migration plan for Phase 0 |
