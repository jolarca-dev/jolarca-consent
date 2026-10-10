# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for `jolarca-consent`.

## What is an ADR?

An ADR captures a significant architectural decision, its context, and its consequences. ADRs are immutable once written; corrections require a new ADR that supersedes the old one.

## ADRs

| ADR | Title | Status | Date |
|---|---|---|---|
| [ADR-0001](ADR-0001-consent-registry-of-record.md) | Independent consent registry of record | Accepted | 2026-09-26 |
| [ADR-0002](ADR-0002-sha256-append-only-chain.md) | SHA-256 append-only hash chain for tamper-evidence | Accepted | 2026-09-26 |
| [ADR-0003](ADR-0003-withdrawal-anonymize-dont-delete.md) | Withdrawal via anonymize-don't-delete (Art. 7 vs Art. 17) | Accepted | 2026-09-26 |
| [ADR-0004](ADR-0004-dpo-article37-assessment.md) | DPO — Art. 37 assessment: not required | Accepted | 2026-09-28 |

## Template

New ADRs should follow this structure:

```markdown
# ADR-NNNN: Title

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]

## Context

What is the issue that we're seeing that is motivating this decision?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

## Compliance mapping

Which compliance controls does this ADR satisfy?

## References

Links to relevant documents, policies, or other ADRs.
```

## House conventions

- ADRs are numbered sequentially (ADR-0001, ADR-0002, ...)
- ADRs are immutable once accepted; corrections require a new ADR
- ADRs must be reviewed by the controller before acceptance (ADR-0004: no DPO designated; sole operator holds all GDPR obligations)
- ADRs are stored in `docs/adr/` and referenced from `docs/architecture.md`
