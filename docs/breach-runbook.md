# Breach Runbook — Consent registry incident response and 72-hour notification

## Purpose

This runbook defines the step-by-step procedure for detecting, containing, assessing, and notifying in the event of a suspected or confirmed personal data breach involving the jolarca-consent registry. It maps each threat from the [threat model](threat-model.md) (T1–T10) to concrete detection signals, containment actions, and notification timelines.

**Legal basis:**

| GDPR Article | Obligation | Covered in this runbook |
|---|---|---|
| Art. 33(1) | Notify supervisory authority within 72 hours of awareness | Section 3 — notification timeline |
| Art. 33(2) | Describe the breach, categories/data subjects affected, likely consequences, measures taken | Section 4 — notification content |
| Art. 34(1) | Communicate breach to data subjects without undue delay when high risk | Section 5 — subject notification |
| Art. 5(1)(f) | Integrity and confidentiality (appropriate security) | Section 6 — post-incident remediation |
| Art. 7(1) | Demonstrability of consent | Section 6 — chain re-verification |

**Supervisory authority:** VDAI (Lithuanian State Data Protection Inspectorate) — the lead authority for the controller's establishment.

## Scope

### What counts as a personal data breach

A personal data breach is a breach of security leading to the accidental or unlawful destruction, loss, alteration, unauthorized disclosure of, or access to, personal data transmitted, stored or otherwise processed (GDPR Art. 4(12)).

For the consent registry, personal data includes:

| Field | Sensitivity | Breach relevance |
|---|---|---|
| `subject_id` (UUID) | Identifier — links consent to a natural person | Unauthorized disclosure, alteration, or loss = breach |
| `ip_address` | Identifier — network-level personal data | Disclosure = breach |
| `user_agent` | Identifier — device fingerprint | Disclosure = breach |
| `purpose`, `consent_version`, `granted`, `timestamp` | Consent metadata — not personal data alone, but personal when linked to `subject_id` | Alteration undermines Art. 7(1) demonstrability |

### Severity classification

| Severity | Criteria | Notification |
|---|---|---|
| **Critical** | Hash chain integrity compromised; append-only bypass confirmed; API key material leaked | Immediate internal escalation; **notify VDAI within 24 h** (do not use the full 72 h window); notify data subjects |
| **High** | Unauthorized read access to personal data; single-record tampering detected by chain verifier | Notify VDAI within 72 h; notify data subjects if high risk to rights and freedoms |
| **Medium** | Anomalous API activity; chain verification transient failure (resolved within verification window) | Internal investigation; notify VDAI only if confirmed breach of personal data |
| **Low** | Failed attack attempts blocked by controls; no data exposure | Internal logging only; no notification required |

## Notification timeline

### 72-hour clock (Art. 33(1))

The 72-hour clock starts when the controller has a **reasonable degree of certainty** that a security incident has occurred and that it involves personal data. This is not when the breach is fully understood — it is when there is enough evidence to conclude that a breach likely occurred.

```
T+0h   Incident detected (alert, anomaly, report)
       └─► Log in incident register (Section 7)
       └─► Page on-call engineer
T+0–4h Initial triage
       └─► Confirm: does this involve personal data?
       └─► Confirm: is this a security incident (not just an outage)?
       └─► If YES to both → clock starts
       └─► Classify severity (Critical / High / Medium / Low)
       └─► If Critical → 24-hour notification target (not 72 h)
T+4–24h Containment and scoping
       └─► Identify affected records (subject_ids, date range, data categories)
       └─► Identify root cause (which threat T1–T10?)
       └─► Preserve evidence (do NOT modify affected records)
       └─► Run offline chain verifier to confirm chain state
       └─► If Critical: draft and submit Art. 33 notification by T+24h
T+24–48h Notification preparation (High severity and below)
       └─► Draft Art. 33 notification (Section 4 template)
       └─► Legal review
       └─► Determine whether Art. 34 subject notification is needed
T+48–72h Notification delivery (High severity and below)
       └─► Submit notification to VDAI
       └─► If high risk: notify affected data subjects (Art. 34)
T+72h–30d Remediation and post-incident
       └─► Apply fix, re-verify chain, update threat model
       └─► Post-incident review within 14 days
       └─► Update controls if gap identified
```

### Decision: does the 72-hour clock apply?

```
Was personal data involved?
├─ NO  → Not a GDPR breach. Log internally. Close.
└─ YES → Was there a breach of security (unauthorized access/disclosure/alterment/destruction)?
         ├─ NO  → Not a GDPR breach (may be an outage). Log internally. Close.
         └─ YES → Is the breach likely to result in a risk to rights and freedoms?
                  ├─ NO  → Not notifiable under Art. 33. Log in breach register. Monitor.
                  └─ YES → NOTIFY VDAI within 72 hours. Proceed to Section 4.
                           └─ Is the risk HIGH?
                                    ├─ NO  → Art. 33 only.
                                    └─ YES → Art. 33 + Art. 34 (notify data subjects too).
```

## Threat-to-breach mapping

Each threat from the [threat model](threat-model.md) is mapped below to: breach type, detection method, containment, 72-hour applicability, and notification obligation.

### T1: Product modifies a record after write via the API

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized alteration of personal data |
| **Personal data affected** | `subject_id`, `ip_address`, `user_agent`, consent metadata of the modified record |
| **Detection** | Chain verification failure (`entry_hash` mismatch); 405 on PUT/PATCH (should never succeed); application log anomaly |
| **Containment** | Revoke the calling product's API key immediately; isolate the affected records; do NOT modify them (preserve evidence) |
| **Chain impact** | The modification breaks the chain. The offline verifier identifies the exact record(s) affected |
| **72-hour clock** | **Starts** when chain verifier reports a mismatch attributable to an API write (not a serialization bug) |
| **Art. 33 (VDAI)** | **Required.** Unauthorized alteration of consent records is a breach of Art. 5(1)(f) and Art. 7(1) |
| **Art. 34 (subjects)** | **Required if high risk.** Affected data subjects whose consent proof was altered face concrete risk (their consent state may have been changed without their knowledge) |

### T2: Product deletes a record via the API

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized destruction of personal data |
| **Personal data affected** | All fields of the deleted record |
| **Detection** | Chain verification failure (gap in `prev_hash` sequence); 405 on DELETE (should never succeed); record count anomaly |
| **Containment** | Revoke the calling product's API key; assess whether the deletion was from the ledger or only from a cache/pointer |
| **Chain impact** | Deletion breaks the chain. The offline verifier identifies the gap |
| **72-hour clock** | **Starts** when chain verifier reports a gap attributable to an API call (not a migration side-effect) |
| **Art. 33 (VDAI)** | **Required.** Destruction of consent evidence is a breach |
| **Art. 34 (subjects)** | **Required.** The data subject's consent proof is gone; high risk to their rights |

### T3: DBA modifies a record directly in the database

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized alteration of personal data (insider threat) |
| **Personal data affected** | `subject_id`, `ip_address`, `user_agent`, consent metadata |
| **Detection** | Chain verification failure; audit log showing admin-role `UPDATE` outside a deployment window |
| **Containment** | Revoke the DBA's admin role access immediately; preserve audit logs; snapshot the affected table state before any remediation |
| **Chain impact** | Modification breaks the chain. The offline verifier identifies the record |
| **72-hour clock** | **Starts** when chain verifier or audit log review confirms the modification |
| **Art. 33 (VDAI)** | **Required.** Insider alteration is a breach of integrity controls |
| **Art. 34 (subjects)** | **Required if high risk.** Depends on what was altered and whether the subject's effective consent state changed |

### T4: DBA deletes a record directly in the database

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized destruction of personal data (insider threat) |
| **Personal data affected** | All fields of the deleted record |
| **Detection** | Chain verification failure (gap in `prev_hash`); audit log showing admin-role `DELETE` |
| **Containment** | Same as T3. Revoke admin access; preserve audit logs; do NOT attempt to "fix" the gap by inserting a replacement — that would create a second chain break |
| **Chain impact** | Deletion breaks the chain |
| **72-hour clock** | **Starts** when the gap is confirmed as unauthorized |
| **Art. 33 (VDAI)** | **Required.** |
| **Art. 34 (subjects)** | **Required.** The data subject lost their consent proof |

### T5: Attacker forges a new chain from a modified genesis

| Attribute | Value |
|---|---|
| **Breach type** | Systematic alteration of personal data + integrity control bypass |
| **Personal data affected** | ALL records in the ledger (every `subject_id`, `ip_address`, `user_agent`) |
| **Detection** | Offline verifier detects genesis mismatch; external anchor mismatch (if RFC 3161 is enabled); chain verification endpoint returns 409 for every record |
| **Containment** | **Critical severity.** Immediately take the registry offline (stop accepting writes); preserve the full database snapshot; engage forensics |
| **Chain impact** | The entire chain is suspect. Cannot determine which records are authentic without external evidence |
| **72-hour clock** | **Starts immediately** on detection. This is the most severe breach scenario |
| **Art. 33 (VDAI)** | **Required. Target: 24 hours.** Notify as soon as the forgery is confirmed — do not wait for full scoping. The 72-hour statutory maximum applies, but mass-subject impact demands notification within 24 h |
| **Art. 34 (subjects)** | **Required.** Every data subject in the ledger is affected. Mass notification required |

### T6: Attacker truncates the ledger (deletes the tail)

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized destruction of personal data |
| **Personal data affected** | All fields of the truncated records |
| **Detection** | Chain verifier reports that the most recent `prev_hash` does not match any record's `entry_hash`; record count anomaly vs. application logs |
| **Containment** | Take the registry offline; preserve the truncated database and any available backups for forensic comparison |
| **Chain impact** | Truncation breaks the chain at the cut point |
| **72-hour clock** | **Starts** when truncation is confirmed |
| **Art. 33 (VDAI)** | **Required.** |
| **Art. 34 (subjects)** | **Required** for subjects whose records were truncated |

### T7: Attacker reorders records

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized alteration of personal data (reordering changes effective consent state) |
| **Personal data affected** | `subject_id`, consent metadata of reordered records |
| **Detection** | Chain verification failure (`prev_hash` mismatch after reorder); `created_at` sequence inconsistency |
| **Containment** | Take the registry offline; preserve the reordered state as evidence |
| **Chain impact** | Reordering breaks the chain |
| **72-hour clock** | **Starts** when reordering is confirmed |
| **Art. 33 (VDAI)** | **Required.** Reordering may change effective consent state (e.g., making a withdrawal appear before a grant) |
| **Art. 34 (subjects)** | **Required if high risk.** Depends on whether the reorder changed any subject's effective consent state |

### T8: Attacker compromises an API key

| Attribute | Value |
|---|---|
| **Breach type** | Unauthorized access; potential unauthorized writes of fraudulent consent records |
| **Personal data affected** | `subject_id`, `ip_address`, `user_agent` in any records written with the compromised key; the key material itself |
| **Detection** | Anomalous write patterns (sudden spike in records, unknown `subject_id`s, writes from unexpected IP); Vault audit log showing key access outside normal schedule |
| **Containment** | Immediately rotate the compromised API key via Vault; revoke all sessions using that key; assess which writes were authorized vs. fraudulent |
| **Chain impact** | The chain itself is NOT broken (fraudulent writes are still valid chain entries). The integrity of the data is the concern, not the integrity of the chain |
| **72-hour clock** | **Starts** when unauthorized writes are confirmed (not when the key leak is suspected — suspicion alone triggers investigation, not notification) |
| **Art. 33 (VDAI)** | **Required** if fraudulent writes involving personal data are confirmed |
| **Art. 34 (subjects)** | **Required if high risk.** Subjects whose data was used in fraudulent consent records are affected |

### T9: Attacker modifies the chain verifier

| Attribute | Value |
|---|---|
| **Breach type** | Integrity control bypass — the detector itself is compromised |
| **Personal data affected** | Potentially ALL records (if the verifier was modified to hide modifications) |
| **Detection** | Adversarial test suite fails; offline verifier (independent, stdlib-only) disagrees with the Django app's verifier; code review catches unauthorized changes to `verify_chain.py` or `hash_chain.py` |
| **Containment** | Immediately run the offline verifier (`scripts/verify_chain.py`) from a known-good checkout; if it also fails, escalate to T5 (forged chain); if it passes, the Django verifier was modified but the chain is intact |
| **Chain impact** | The chain may be intact (verifier modified but data untouched) or compromised (verifier modified to hide data changes). Must determine which before scoping |
| **72-hour clock** | **Starts** when it is determined that the verifier modification was hiding actual data changes. If the chain is intact, this is a security incident but NOT a personal data breach (no data was exposed/altered) |
| **Art. 33 (VDAI)** | **Required only if** the verifier modification was hiding actual data changes. If the chain is intact, no notification — but document the incident |
| **Art. 34 (subjects)** | **Required only if** personal data was actually altered |

### T10: Attacker modifies the canonical serialization

| Attribute | Value |
|---|---|
| **Breach type** | Integrity control bypass — hash computation is compromised |
| **Personal data affected** | Potentially ALL records (if serialization was modified to produce different hashes for altered data) |
| **Detection** | Adversarial test suite fails; offline verifier (which implements its own serialization) disagrees with the Django app's hashes |
| **Containment** | Same as T9. Run the offline verifier from a known-good checkout. Compare canonical serialization output byte-for-byte against the offline verifier |
| **Chain impact** | Same as T9 — chain may or may not be intact depending on whether the serialization change was hiding data modifications |
| **72-hour clock** | **Starts** when it is determined that the serialization modification was hiding actual data changes |
| **Art. 33 (VDAI)** | **Required only if** personal data was actually altered |
| **Art. 34 (subjects)** | **Required only if** personal data was actually altered and risk is high |

## Summary matrix

| Threat | Breach type | Detection signal | 72-hour clock starts | Art. 33 | Art. 34 |
|---|---|---|---|---|---|
| T1 | Alteration | Chain mismatch | On confirmation | Yes | If high risk |
| T2 | Destruction | Chain gap | On confirmation | Yes | Yes |
| T3 | Alteration (insider) | Chain mismatch + audit log | On confirmation | Yes | If high risk |
| T4 | Destruction (insider) | Chain gap + audit log | On confirmation | Yes | Yes |
| T5 | Systematic forgery | Genesis mismatch | Immediately | Yes (urgent) | Yes (mass) |
| T6 | Destruction (truncation) | Chain tail break | On confirmation | Yes | If high risk |
| T7 | Alteration (reorder) | Chain mismatch + sequence anomaly | On confirmation | Yes | If high risk |
| T8 | Unauthorized access/writes | Anomalous write patterns | On confirmation of fraudulent writes | If confirmed | If high risk |
| T9 | Control bypass | Verifier disagreement | Only if data was actually altered | Only if data altered | Only if data altered |
| T10 | Control bypass | Serialization disagreement | Only if data was actually altered | Only if data altered | Only if data altered |

## Notification content template (Art. 33(2))

The notification to VDAI must contain:

```
NOTIFICATION OF PERSONAL DATA BREACH — GDPR Art. 33

1. Controller identity
   - Name: [controller legal entity name]
   - Contact: [DPO name, email, phone]
   - Representative (if applicable): [name, contact]

2. Description of the breach
   - Nature: [alteration / destruction / disclosure / unauthorized access]
   - Threat classification: [T1–T10, reference this runbook]
   - Date of detection: [YYYY-MM-DD HH:MM UTC]
   - Estimated date of occurrence: [YYYY-MM-DD or "unknown — investigation ongoing"]
   - Duration: [single event / ongoing since DATE]

3. Categories and approximate number of data subjects affected
   - Categories: [e.g., marketplace users who granted consent]
   - Approximate number: [N]

4. Categories and approximate number of personal data records affected
   - Data categories: [subject_id, ip_address, user_agent, consent metadata]
   - Approximate number of records: [N]

5. Likely consequences
   - [Describe the risk to data subjects, e.g., "consent proof for purpose X
     was altered, potentially affecting the lawfulness of processing between
     DATE and DATE"]

6. Measures taken or proposed
   - Containment: [API key revoked / access revoked / service taken offline]
   - Chain re-verification: [offline verifier run, result]
   - Remediation: [fix deployed, controls updated]
   - Subject notification: [yes/no, if yes — method and date]
```

## Containment actions by severity

| Severity | Immediate actions (< 1 hour) |
|---|---|
| **Critical** (T5, T9/T10 with data alteration) | Take registry offline; preserve database snapshot; page all on-call; engage forensics; notify VDAI within 24 h (do not use the full 72 h) |
| **High** (T1–T4, T6–T8 confirmed) | Revoke implicated API key or admin access; run offline chain verifier; preserve evidence; begin scoping |
| **Medium** (T8 suspected, T9/T10 without data alteration) | Increase chain verification frequency to every 15 min; investigate; escalate if confirmed |
| **Low** (blocked attempts) | Log and monitor; no containment needed |

## Post-incident remediation

Within 14 days of incident closure:

1. **Root cause analysis** — document in the incident register entry
2. **Chain re-verification** — run `python scripts/verify_chain.py` and confirm the chain is intact end-to-end
3. **Control update** — if the breach exploited a gap in controls, close the gap:
   - T1/T2: Review API endpoint configuration; confirm no PUT/PATCH/DELETE routes exist
   - T3/T4: Review admin role access policy; tighten audit log shipping
   - T5: Evaluate RFC 3161 external anchoring (threat model open question)
   - T8: Rotate all API keys (not just the compromised one); review Vault access logs
   - T9/T10: Rebuild verifier from known-good source; add additional adversarial test cases
4. **Threat model update** — if the breach revealed a new attack vector not covered by T1–T10, add it
5. **Notification effectiveness review** — if Art. 34 notification was sent, assess whether subjects understood and could act on it

## Incident register

Maintain a register of all security incidents involving the consent registry. This register is a compliance artifact.

| Field | Description |
|---|---|
| `incident_id` | Unique identifier (e.g., `INC-2026-001`) |
| `detected_at` | Date and time of detection (T+0) |
| `detection_method` | How it was found (chain verifier alert, audit log review, external report) |
| `threat_classification` | T1–T10 or "new" if not yet classified |
| `severity` | Critical / High / Medium / Low |
| `personal_data_involved` | Boolean |
| `72h_clock_started` | Boolean + timestamp |
| `art_33_notified` | Boolean + date |
| `art_34_notified` | Boolean + date + number of subjects notified |
| `records_affected` | Approximate number |
| `subjects_affected` | Approximate number |
| `containment_actions` | What was done to stop the breach |
| `root_cause` | Determined root cause |
| `remediation` | What was done to prevent recurrence |
| `closed_at` | Date the incident was closed |
| `post_incident_review` | Date of the 14-day review |

**Storage:** The incident register is maintained in `jolarca-compliance` alongside the DSAR register. It contains no personal data — only incident metadata.

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-28 | 1.0 | Agent | Initial breach runbook mapping T1–T10 to 72-hour notification |
