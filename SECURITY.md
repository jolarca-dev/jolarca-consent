# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

### Severity levels

| Severity | Examples | Response time |
|---|---|---|
| **Critical** | Hash chain bypass, append-only bypass, API key leak, personal data in git | 24 hours |
| **High** | Consent schema bypass, unauthorized data access, CVE in dependency | 72 hours |
| **Medium** | Information disclosure, CSRF, rate limiting bypass | 7 days |
| **Low** | Minor information leak, non-sensitive data exposure | 30 days |

### How to report

1. **Email:** security@jolarca.com (encrypted with PGP if possible)
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. **Do NOT:**
   - Open a public issue
   - Disclose the vulnerability publicly before it is fixed
   - Attempt to exploit the vulnerability beyond what is necessary to demonstrate it

### What to expect

1. **Acknowledgment:** Within 24 hours (Critical/High) or 72 hours (Medium/Low).
2. **Assessment:** We will assess the severity and validate the vulnerability.
3. **Fix:** We will develop and test a fix.
4. **Disclosure:** We will coordinate disclosure with you. Typically 30 days after the fix is deployed.
5. **Credit:** We will credit you in the security advisory (unless you prefer to remain anonymous).

## Security controls

### Append-only guarantee

- ORM guard: `ConsentRecord.save()` raises on update.
- DB-level: Application role has `INSERT` only; `UPDATE`/`DELETE` revoked.
- Hash chain: SHA-256 prev-hash chain; any modification breaks the chain.
- Offline verifier: `scripts/verify_chain.py` detects tampering.

### API authentication

- API keys stored in Vault, injected at runtime.
- HMAC-signed requests.
- Least-privilege: each caller gets only the permissions it needs.

### Data protection

- No personal data in git (enforced by `gitleaks` and `detect-private-key` in pre-commit).
- Encryption at rest (pgcrypto or infrastructure-level disk encryption).
- Encryption in transit (TLS 1.3).

### Monitoring and alerting

- Chain verification runs on every deployment + daily schedule.
- Alerts on chain verification failure (highest severity).
- Audit logs for all API calls.

## Security advisories

Security advisories are published at <https://github.com/jolarca-dev/jolarca-consent/security/advisories>.

## Revision history

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-09-26 | 1.0 | Agent | Initial security policy for Phase 1 |
