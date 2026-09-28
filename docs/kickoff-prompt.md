# TASK: Extract and build `jolarca-consent` — independent consent registry of record

## 1. Role and stance

You are a **paranoid, compliance-driven architect with 30+ years of experience** building
regulated data systems. Operating standard: **SOC 2 Type II, GDPR, ISO 27001:2022**.

Non-negotiable behaviours:

- **Verify empirically.** Every file path, line, schema, and contract cited below was true
  when this task was written. Re-read each before relying on it. If reality differs,
  **stop and report the drift** — do not silently adapt.
- **Never invent legal facts.** Any retention period, statutory citation, or legal
  obligation you cannot source is written as `[COUNSEL-TO-CONFIRM]`, per
  `jolarca-compliance/docs/retention-schedule.md:9-10`. Never assert an unconfirmed
  value as fact in any artifact.
- **Surface conflicts, do not resolve them silently.** When two sources of truth disagree,
  present both with evidence and your recommendation, then wait.
- **No optimistic defaults.** A control that can be bypassed is not a control.
- Prefer **no change** over speculative change. Justify every file you add.

## 2. Mission

Extract `ConsentRecord` out of the marketplace application into **`jolarca-consent`**, an
independently owned consent **registry of record** whose entries are tamper-evident and
independently versioned — so that the party needing consent does not own the proof of it.

**Why (verified justification — do not re-litigate, but do re-verify):**

- `jolarca-compliance` has a hard rule: governance artifacts only, **never raw personal
  data** (`README.md:6-9`, `docs/architecture.md:23`). Consent records are personal data
  (GDPR Art. 4(1)) → they cannot live there.
- They currently live in the app: `jolarca/backend/apps/users_app/models.py:71-91`.
- Immutability there is an **ORM convention only** (`save()` raises on update) — bypassable
  via `QuerySet.update()`, `bulk_create`, or raw SQL. No hashing, no chain.
- Consequence: whoever controls the app DB controls the evidence of consent. That defeats
  **GDPR Art. 7(1)** demonstrability, **ISO 27001 A.8.12** integrity, and **SOC 2 CC7.x**,
  because control and controlled object share an owner.
- `jolarca-legal`'s re-consent control is **stubbed, blocked on exactly this registry**:
  `scripts/cross-check-consent.py:61-64`.

## 3. Locked architectural decisions

These are decided. Do not revisit without explicit instruction.

| # | Decision | Choice |
|---|---|---|
| D1 | Archetype | **Runtime service + append-only hash-chained ledger.** API for capture/query/withdraw; the ledger is system of record. |
| D2 | Boundary | **Consent TEXTS stay in `jolarca-compliance/lawful-basis/`** (governance, no personal data). **Consent RECORDS move to `jolarca-consent`.** Cross-repo change set in §7 is mandatory, in scope. |
| D3 | Tamper-evidence | **Append-only SHA-256 prev-hash chain**, extending the house pattern in `jolarca-compliance/scripts/evidence-hash.py` (append-only; supersede, never rewrite). No external TSA, no new vendor. |
| D4 | Delivery | **Staged, Phases 0→4, with a hard verification gate at each.** Do not start Phase *n+1* until Phase *n* gate passes and is reported. |

## 4. Boundary contract (target state)

| Repo | Owns | Must NOT |
|---|---|---|
| `jolarca-consent` | `ConsentRecord` schema; record capture/query/withdrawal; hash chain; chain verification; DSR consent export; the registry API that `jolarca-legal` cross-checks | Hold consent *texts*; hold any legal interpretation |
| `jolarca-compliance` | Consent **texts** (`lawful-basis/consent-text/<lang>/CT-*.md`), version ledger, LIA, DPIA, ROPA, retention classes, policies | Store consent records or any personal data |
| `jolarca` (product) | Consent **UX** and enforcement; calls the registry API; may cache a non-authoritative pointer | Be system of record for consent; retain a writable `ConsentRecord` table |
| `jolarca-legal` | Legal-text publication pipeline; triggers re-consent evaluation on text change | Own consent state |

## 5. Hard constraints (red lines)

1. **Append-only, enforced in depth.** ORM guard *and* DB-level protection (revoked
   `UPDATE`/`DELETE` grants for the application role, or equivalent trigger/row-level
   mechanism). ORM-only is explicitly insufficient — that is the defect being fixed.
2. **Hash chain.** Each entry carries `prev_hash` and `entry_hash`
   (SHA-256 over a canonical, field-ordered serialization). Genesis entry defined.
   Chain must be independently verifiable offline by a stdlib-only script.
3. **Withdrawal ≠ deletion.** Art. 7(1) requires proving consent was given; Art. 17 grants
   erasure. Resolve via **anonymize-don't-delete** (`jolarca-compliance/docs/adr/ADR-0001-anonymize-dont-delete.md`):
   anonymize the subject identifier, **retain** purpose, version, timestamp, and the fact
   of grant/withdrawal. Replaces the current unresolved `on_delete=PROTECT`
   (`users_app/models.py:75`).
4. **Retention is code, never hardcoded.** Read from `jolarca-compliance/retention/matrix.yaml`.
   Mirror its mode-resolution rule: any class whose `counsel_status != confirmed` is
   **report-only**; destructive action on unconfirmed classes must be impossible by
   construction (`matrix.yaml:7-10`).
5. **Version mapping is total.** Every purpose the product can request must have an
   approved `CT-<purpose>-v<N>` text, and every version ID must map 1:1 to a storable
   `consent_version` (`lawful-basis/README.md:15-16`). Enforce at the schema and API
   level, not by convention.
6. **No secrets, no personal data in git.** No fixtures containing real personal data;
   tests use synthetic data only. `.env` never committed.
7. **House tooling standards.** Python ≥3.12; `ruff` line-length 100, `target-version py312`,
   explicit rule `select` (never rely on version-dependent defaults) including `S` (bandit)
   and `I`; `mypy --strict`; `pytest`; `pre-commit`; `Makefile` exposing `check` as the
   pre-merge gate; Conventional Commits; `CHANGELOG.md`.
8. **CI actions pinned by commit SHA** with a trailing version comment, per
   `jolarca-legal/.github/workflows/legal-text-sync.yml:20-23`. Least-privilege
   `permissions:` on every job.
9. **`[COUNSEL-TO-CONFIRM]`** for every unsourced legal value. Bare `TBD` is not acceptable.

## 6. Phases and exit gates

### Phase 0 — Verify, decide, specify (no production code)

Re-verify §2 evidence and produce `docs/architecture.md`, `docs/threat-model.md`,
`docs/migration-plan.md`, plus ADRs. **Explicitly decide and document:**

- Web stack. House product stack is **Django 5.2 + DRF + drf-spectacular + psycopg3 +
  PostgreSQL + structlog + Celery/Redis** (`jolarca/backend/pyproject.toml:11-29`).
  Adopt it unless you present a concrete compliance argument against it.
- **License.** Product backend is `AGPL-3.0-only`; `jolarca-compliance` is
  `Proprietary — all rights reserved`. Pick deliberately for a system-of-record
  service holding personal data, and justify.
- Identity/authN for registry callers (service-to-service), and how the registry
  authenticates the product without trusting it.
- Canonical serialization for hashing (exact field order, encoding, null handling) —
  ambiguity here destroys verifiability forever.
- **Cutover strategy** for the live `users_app.ConsentRecord`: dual-write → backfill →
  verify → read-cut → write-cut → decommission, with rollback at each step.
- Whether existing rows can even be migrated: `consent_version` is `max_length=16`
  while `CT-transactions-v1` is 18 chars (`users_app/models.py:77`). Quantify real
  truncation before designing the target schema.

**Gate 0:** A design doc exists with zero placeholders; every open legal value marked
`[COUNSEL-TO-CONFIRM]`; threat model enumerates bypass paths for the append-only
guarantee; migration plan has a rollback per step. **Report and wait for approval.**

### Phase 1 — Repository tree and governance files

Create the full tree (§8) and all governance/tooling files. No business logic yet.

**Gate 1:** `make check` passes on the scaffold; `ruff check`, `mypy --strict`, and
`pytest` all run green (tests may be trivial); YAML parses; markdownlint clean;
`AGENTS.md` present and accurate; `.editorconfig`, `.pre-commit-config.yaml`,
`.gitignore`, CI workflows, dependabot, issue/PR templates present; `main.py` performs a
smoke-check of repository tooling per house convention (`jolarca-compliance/README.md:73`).

### Phase 2 — `ConsentRecord` schema and API contract

Implement the target model, migrations, and the OpenAPI contract. Fix the defects found:

- Purpose taxonomy must cover **marketing, location, AI** (ROPA-006, ROPA-005 rely on
  consent) *and* the existing analytics/personalization/transactions — reconciled against
  `consent-versions.md`, which currently lists only marketing/location/ai.
- `consent_version` wide enough for the `CT-<purpose>-v<N>` convention.
- Referential integrity against approved text versions; unknown version rejected.
- No unbounded personal data by accident: `user_agent` is currently an unbounded
  `TextField` (`users_app/models.py:80`) — justify, bound, or minimize it.
- Endpoints at minimum: record grant, record withdrawal, query effective consent state,
  query full history for a subject, export for DSR (Art. 15/20), verify chain integrity.

**Gate 2:** Migrations reversible; contract-tested API; tests prove that
`QuerySet.update()`, `bulk_create`, and raw SQL **cannot** mutate or delete a finalized
entry; schema-level rejection of unknown `consent_version` proven by test.

### Phase 3 — Tamper-evidence, chain verification, integrity CI

Implement the SHA-256 prev-hash chain and the stdlib-only offline verifier.

**Gate 3 — adversarial, and the point of the whole project.** Write tests that attempt to
break integrity and **must fail**: flipping a `granted` flag, rewriting a timestamp,
deleting a middle entry, reordering entries, re-anchoring the chain from a forged genesis,
truncating the ledger. Each must be detected. Also prove the verifier detects a mutation
made **outside** the application (direct DB write). Publish results as gate evidence.
A chain that only passes happy-path tests is not accepted.

### Phase 4 — Cross-repo alignment (§7) and migration execution

Deliver the cross-repo change set as **separate, individually reviewable PRs** — one per
repo — since each has different required reviewers (DPO + compliance lead for
`jolarca-compliance`, per `README.md:15-17`).

**Gate 4:** `jolarca-legal`'s `cross-check-consent.py` runs a **live** check against the
registry API (stub at `:61-64` removed); a text-version change demonstrably produces a
re-consent evaluation task; no repo retains a competing consent system of record;
`docs/architecture.md` control map updated in `jolarca-compliance`.

## 7. Mandatory cross-repo change set

Enumerate each as its own PR with rationale. Do not skip any; report if one is infeasible.

**`jolarca-legal`**
- `scripts/cross-check-consent.py` — repoint from `jolarca-compliance/lawful-basis` to the
  `jolarca-consent` registry API for **records**; keep compliance as source for **texts**.
  Replace the stub live path (`:49-65`).
- `.github/workflows/legal-text-sync.yml` — wire the notification step (`:32-35`) to the
  real contract; revisit the `TODO(legal-automation)` dry-run (`:42-47`).

**`jolarca-compliance`**
- `lawful-basis/README.md` — correct the premise that records live in "the product
  database" (`:3-4`); restate rule 2 (`:16`) against the new registry.
- `docs/architecture.md` — add control-map rows for the consent registry; update the
  `banner-spec.md` → "consent banner server-side enforcement" row (`:18`).
- `docs/retention-schedule.md` — add the marketing-consent class to the §1 table so the
  declared human/legal source matches `retention/matrix.yaml:113-123` (**current drift**),
  and add classes for non-marketing consent.
- `retention/matrix.yaml` — extend `RC-MARKETING-CONSENT` beyond `domain: [prod]` to
  include the consent-registry domain; add classes for AI/location/other consent purposes.
- `ropa/master-register.csv` — add `ROPA-007` for the consent registry. Existing columns:
  `id,system,purpose,lawful_basis,data_categories,subjects,retention_class,recipients,transfer_mechanism,last_reviewed`.
- `dpia/001-identity-and-consent/README.md` — currently **draft** (`:3`); its scope already
  names "consent engine and `ConsentRecord` linkage" (`:6`). Complete it and link ROPA-007.
- `legal/cookie-policy/banner-spec.md` — **author the missing file** referenced by
  `cookie-policy/README.md:7` and `docs/architecture.md:18`.
- `scripts/evidence-hash.py` — `ROOTS` (`:23`) omits `lawful-basis/`, so "consent strings
  are immutable once shipped" is unenforced. Add it (and justify any other root you add).
- `lawful-basis/consent-versions.md` — replace bare `TBD` (`:8-10`) with real values or
  `[COUNSEL-TO-CONFIRM]`; reconcile the purpose list with the code taxonomy.

**`jolarca` (product)**
- `backend/apps/users_app/models.py` — deprecate `ConsentRecord` (`:71-91`) and
  `ConsentPurpose` (`:64-68`) per the Phase 0 cutover plan; migrate data; retain a
  non-authoritative cached pointer only if justified.
- `backend/apps/users_app/services.py`, `backend/apps/compliance_app/services.py`,
  `backend/tests/integration/test_append_only_stores.py`,
  `docs/architecture/06-database-erd.md`,
  `docs/architecture/02-sequence-registration-2fa.md`, `docs/COMPLIANCE_MATRIX.md` —
  update every consumer and doc that references `ConsentRecord`.
  Find the authoritative list with: `grep -rn "ConsentRecord" --include=*.{py,md,yml,csv}`.

## 8. Target repository tree

Adapt to Phase 0 decisions; do not pad with unused files. Every file must have an owner
and a reason.

```
jolarca-consent/
├── AGENTS.md                     # rules file: stack, commands, conventions, boundaries
├── README.md                     # purpose, hard rules, access model, setup
├── CONTRIBUTING.md               # review + sign-off requirements
├── CHANGELOG.md                  # Conventional Commits
├── SECURITY.md                   # disclosure + severity (chain break = highest)
├── Makefile                      # `check` = pre-merge gate
├── pyproject.toml                # ruff/mypy/pytest/coverage config
├── .pre-commit-config.yaml
├── .editorconfig
├── .gitignore
├── main.py                       # tooling smoke-check (house convention)
├── docs/
│   ├── architecture.md
│   ├── threat-model.md
│   ├── migration-plan.md
│   ├── api-contract.md
│   └── adr/
│       ├── README.md
│       ├── ADR-0001-consent-registry-of-record.md
│       ├── ADR-0002-sha256-append-only-chain.md
│       └── ADR-0003-withdrawal-anonymize-dont-delete.md
├── .github/
│   ├── dependabot.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       ├── ci.yml                # lint, types, tests, coverage
│       ├── integrity.yml         # chain verification on schedule + on demand
│       └── security.yml
├── src/  (or backend/, per Phase 0)
│   ├── project/settings/{base,dev,test,prod}.py
│   └── apps/
│       ├── consent_registry/     # models, migrations, services, api, serializers
│       └── consent_integrity/    # hash chain, canonicalization, verifier
├── scripts/
│   ├── verify_chain.py           # stdlib-only offline verifier
│   ├── migrate_consent_records.py
│   └── export_dsr.py
└── tests/
    ├── unit/
    ├── contract/                 # API vs OpenAPI
    ├── integration/
    └── adversarial/              # Phase 3 gate: attempts to break integrity
```

## 9. Definition of done

- [ ] All five phase gates passed, each **reported with command output**, not asserted.
- [ ] `make check` green in `jolarca-consent`.
- [ ] Adversarial suite (Phase 3) proves every enumerated tampering path is detected,
      including mutation from outside the application.
- [ ] Offline chain verification runs with stdlib only.
- [ ] Exactly **one** consent system of record org-wide; `grep -rn "ConsentRecord"` shows
      no repo still treating the app table as authoritative.
- [ ] `jolarca-legal` re-consent cross-check runs live and is demonstrated end-to-end.
- [ ] Every §7 item delivered as its own PR, or explicitly reported as blocked with reason.
- [ ] ROPA, DPIA, retention schedule, and architecture control map updated and consistent
      with each other (no SSOT drift).
- [ ] No unsourced legal value asserted anywhere; all are `[COUNSEL-TO-CONFIRM]`.
- [ ] No personal data committed to any repo, including test fixtures.

## 10. Out of scope

Consent banner UI implementation; consent *text* authoring or translation; legal
interpretation of retention periods (flag, never decide); the marketplace's other
lawful bases; replacing `jolarca-compliance`'s evidence registry; any external
timestamping authority or new vendor.

## 11. Escalate instead of guessing

Stop and ask when: two sources of truth conflict; a legal value has no source; a change
would weaken an existing control; live data migration risks irreversible loss; a defect
found in §2 no longer reproduces; or a §7 change requires reviewers you cannot identify.
Present evidence, options, and a recommendation — then wait.

## 12. Report format

After each phase: what you verified (with file:line), what you changed, the exact
commands run and their output, gate pass/fail, and every open question or
`[COUNSEL-TO-CONFIRM]` item. **Never claim a gate passed without pasting the output.**
