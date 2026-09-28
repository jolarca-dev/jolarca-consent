# Contributing to jolarca-consent

This repository has stricter rules than a typical code repository. The consent ledger is compliance evidence; integrity is the product.

## Evidence-handling rules

1. **Append-only, enforced in depth.** The consent ledger is append-only at the ORM level *and* DB level. ORM-only is insufficient. Any modification breaks the hash chain and is detected by the offline verifier.
2. **No deletion of finalized records.** Consent records are never deleted. Withdrawal is recorded as a new entry (or an anonymization event). Git history must never be rewritten for this repo (`--force-push`, history rewrite = Critical incident, see SECURITY.md).
3. **No personal data in git.** No fixtures containing real personal data; tests use synthetic data only. `.env` never committed. `gitleaks` and `detect-private-key` run in pre-commit as a backstop, not as a license to be careless.
4. **Commits are audit history.** Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `compliance:`). Every compliance-relevant change must appear in `CHANGELOG.md`.

## Pull request requirements

- PR template checklist fully answered.
- CODEOWNERS approval: `docs/adr/`, `docs/architecture.md`, `docs/threat-model.md` require DPO + compliance lead.
- CI green: `make check` (ruff, mypy, pytest, markdownlint, YAML validation, chain verification).

## Branching

- `main` is protected: no direct pushes, no force pushes, linear history.
- Long-lived branches are discouraged; merge via PR.

## Classification labels

| Label | Meaning | Extra requirement |
|---|---|---|
| `compliance:critical` | Alters the append-only guarantee or hash chain | DPO + compliance lead approval + adversarial test |
| `compliance:high` | Alters consent schema or API contract | DPO approval |
| `compliance:medium` | Alters retention or anonymization logic | Compliance lead approval |

## Development workflow

1. Create a feature branch from `main`.
2. Make changes, following the conventions in `AGENTS.md`.
3. Run `make check` locally.
4. Push and open a PR.
5. Address review comments.
6. Merge via squash or rebase (no merge commits).

## Reporting issues

- **Security vulnerabilities:** See `SECURITY.md`.
- **Bugs:** Open an issue with the `bug` label.
- **Feature requests:** Open an issue with the `enhancement` label.
