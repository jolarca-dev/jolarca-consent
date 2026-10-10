## Description

<!-- Describe the changes in this PR -->

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Compliance-relevant change (requires controller review per ADR-0004)

## Compliance checklist (if applicable)

- [ ] No personal data committed (fixtures use synthetic data only)
- [ ] No secrets committed (API keys via Vault only)
- [ ] Append-only guarantee preserved (no UPDATE/DELETE on consent records)
- [ ] Hash chain integrity preserved (offline verifier passes)
- [ ] ADR added/updated (if architectural decision)
- [ ] CHANGELOG.md updated

## Testing

<!-- Describe the testing you've done -->

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Adversarial tests added/updated (if compliance-relevant)
- [ ] `make check` passes locally

## Additional context

<!-- Add any other context about the PR here -->
