# ADR-0004: Data Protection Officer — Art. 37 assessment: not required

## Status

Accepted

## Context

**The obligation:**

GDPR Article 37(1) mandates the designation of a Data Protection Officer (DPO) in three cases:

- **(a)** The processing is carried out by a public authority or body (except courts acting in their judicial capacity).
- **(b)** The core activities of the controller or processor consist of processing operations which require regular and systematic monitoring of data subjects on a **large scale**.
- **(c)** The core activities consist of processing on a **large scale** of special categories of data (Art. 9) or personal data relating to criminal convictions and offences (Art. 10).

**Current state:**

Multiple compliance artifacts in this repository reference a "DPO" role — README access table (`DPO | Admin`), CONTRIBUTING.md label-approval matrix (`DPO + compliance lead approval`), PR template (`requires DPO/compliance lead review`), and architecture data-flow diagrams (`DPO or automated system calls GET /api/v1/dsr/export`). No DPO exists. The controller is a sole operator (`@JourneyOfLife`); there are no teams, no organizational roles, and no second human with repository access (confirmed by CODEOWNERS: `* @JourneyOfLife`).

Referencing a fictional role in compliance artifacts is worse than having no role at all: it creates a false impression of oversight, undermines audit credibility, and violates the evidentiary honesty principle that underpins the consent registry's own design.

## Decision

**A mandatory DPO is not required.** The assessment against each Art. 37(1) criterion:

| Criterion | Assessment | Result |
|---|---|---|
| **(a) Public authority/body** | The controller is a private marketplace platform operated by a sole individual. Not a public authority or body. | Not met |
| **(b) Large-scale regular/systematic monitoring** | The consent registry records consent grants and withdrawals submitted by the product's UI. It does not monitor, track, or profile data subjects behaviourally. Processing volume is bounded by the marketplace's user base across three Baltic markets (LT, LV, EE) — not "large scale" within the meaning of the GDPR. | Not met |
| **(c) Large-scale special/criminal data** | The registry processes ordinary personal data (subject UUID, IP address, user agent, consent metadata). No Art. 9 special categories (health, biometrics, political opinions, etc.) and no Art. 10 criminal-conviction data. **Caveat:** if KYC/AML identity verification begins collecting identity documents with potential Art. 9 data (e.g., biometric photos), this criterion must be reassessed — the determination depends on what is actually verified, not what could be. Counsel must confirm before KYC scope changes. | Not met (counsel-confirmed) |

Since none of the three mandatory-designation triggers are met, **no DPO is required under Art. 37(1).**

**Voluntary appointment is deferred.** A controller may voluntarily designate a DPO (Art. 37(4)), and the same requirements apply to a voluntary DPO (Art. 37(5)). At the current scale — sole operator, three Baltic markets, no special-category data — the cost of a formal DPO appointment (independence guarantee, resource provision, reporting-line separation, Art. 38-39 task bundle) outweighs the compliance benefit. The controller assumes the responsibilities that a DPO would otherwise hold:

- Monitoring GDPR compliance (Art. 39(1)(b)) — the controller reviews all compliance artifacts personally.
- Advising on DPIAs (Art. 39(1)(c)) — the controller conducts DPIAs as required by Art. 35.
- Cooperating with the supervisory authority (Art. 39(1)(d)) — the controller is the single point of contact for the Lithuanian State Data Protection Inspectorate (VDAI).

**Reassessment triggers.** This decision is time-bound and event-driven. It must be revisited when **any** of the following occur, whichever comes first:

| # | Trigger | Rationale |
|---|---|---|
| 1 | **First live user** — a consent record is written for a real data subject in production | Criterion (b) "large scale" engages the moment processing is no longer hypothetical; WLZ/AG/WCD guidance ties the threshold to actual data-subject count |
| 2 | **KYC/AML scope change** — any KYC or AML process begins collecting identity documents with potential Art. 9 data (biometric photos, health data) | Criterion (c) may engage; counsel must confirm before processing begins |
| 3 | **Processing expansion** — the consent registry processes data for more than 3 distinct purposes | Broader processing scope increases the likelihood that systematic monitoring or special-category data is involved |
| 4 | **Market expansion** — the marketplace expands beyond the three Baltic markets (LT, LV, EE) into additional EU/EEA jurisdictions | Multi-jurisdiction processing increases supervisory scrutiny and the probability of Art. 37(1)(b) engagement |
| 5 | **Second operator** — any second person gains access to the consent registry's database or codebase | Separation-of-duties concerns and the D-04 exit trigger per CODEOWNERS |
| 6 | **Regulatory action** — any communication from a supervisory authority (e.g., VDAI) regarding the marketplace's processing | A supervisory authority may determine that a DPO is required regardless of the controller's self-assessment |
| 7 | **Calendar** — 12 months from the assessment date (2026-09-28), whichever trigger fires first | Living control, not a snapshot; annual reassessment ensures the assessment tracks reality |

## Consequences

**Positive:**

- Eliminates fictional roles from compliance artifacts, restoring audit credibility.
- Removes an impossible approval bottleneck (no DPO exists to approve ADRs, PRs, or compliance labels).
- Clarifies that the controller personally holds all GDPR accountability obligations.

**Negative:**

- No independent oversight function beyond the controller's self-review. Mitigated by: the tamper-evident design (hash chain, append-only ledger, offline verifier) provides technical enforcement of compliance controls independent of any human role.
- If the reassessment triggers fire, a DPO must be appointed before processing continues under the new scope.

**Neutral:**

- The supervisory authority (VDAI) can still be contacted directly by data subjects under Art. 77; no DPO intermediary is needed or expected at this scale.

## Compliance mapping

| Control | How satisfied |
|---|---|
| GDPR Art. 37(1) | Formal assessment documents that no mandatory-designation criterion is met |
| GDPR Art. 37(4) | Voluntary appointment explicitly deferred with documented reasoning |
| GDPR Art. 5(2) accountability | Controller acknowledges personal responsibility for all GDPR obligations |
| ISO 27001 A.8.9 | Configuration management: role assignments reflect reality, not aspirational structure |

## References

- GDPR Article 37 — [Designation of the data protection officer](https://gdpr-info.eu/art-37-gdpr/)
- GDPR Articles 38-39 — Position and tasks of the DPO
- EDPB Guidelines on DPOs (WP 243 rev.01) — "large scale" interpretation
- `.github/CODEOWNERS` — sole operator `@JourneyOfLife`, zero teams (D-10)
- `docs/architecture.md` — system context and data flows
- `docs/threat-model.md` — threat actors and mitigations

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-28 | 1.0 | Agent | Initial Art. 37 assessment |
| 2026-09-28 | 1.1 | Agent | Strengthened reassessment triggers (7 event-driven + calendar); added KYC/Art. 9 caveat to criterion (c) |
