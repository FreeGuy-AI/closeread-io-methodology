---
finding_category: credentials
severity_observed: medium
remediation_effort: S
detection_method: hybrid
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# High-entropy secret assigned in production API path

## What the audit found

A TypeScript codebase, document-signing category. In a production tRPC handler that updated an enterprise SSO portal configuration, the audit surfaced a high-entropy variable assignment that looked like:

```
const encryptionKey = SOMETHING_ENCRYPTION_KEY;
```

The variable was sourced from an environment-driven constant, not hardcoded. But the surrounding context (an enterprise-tier authentication endpoint, an `encryptionKey` name, no rotation comment, no key-version reference) flagged it for human review.

This is the pattern that pure regex secret scanners miss. The value at the right-hand side was not a literal string, so naive scanners would have ignored it. The audit elevated it because the **shape of the code around the assignment** matched a credentials-handling pattern in a production path.

## How the audit caught it

Hybrid. Deterministic Stage 1: regex + entropy detector flags any variable assignment where the LHS name contains `key`, `token`, `secret`, `password`, or `credential`. LLM Stage 2: a small classifier scans the surrounding 20 lines for signals like "rotation," "version," "vault," "managed-by," and reduces severity if any are present. None were here, so the finding stayed at MEDIUM.

The audit explicitly notes the confidence as 48%, not 90%. This is intentional. The audit is communicating to the reader that this is a finding worth checking, not a finding that has been confirmed exploitable.

## Why it matters to a buyer

Even when the value is sourced from an environment variable (and is therefore not technically a leaked secret), a buyer's security DD lead reads three things into this finding:

1. **No key rotation strategy is visible.** If there were one, the code would reference a key version or a rotation timestamp.
2. **No key vault abstraction.** The code reaches directly to a process-level constant. A mature codebase wraps this in a `KeyManager.get('encryption-key')` interface that handles rotation, versioning, and the inevitable migration from env-var to vault-backed lookup.
3. **Enterprise tier suggests a high blast radius.** This is the encryption key for enterprise SSO portal configuration. If it ever does leak, it is on the critical path for enterprise customer data.

The audit finding alone is not deal-blocking. The questions it raises in DD frequently are.

## Recommended remediation

1. **Wrap the lookup in a key-management abstraction** that hides whether the value comes from env, vault, or a managed service. This is a one-day refactor in a small codebase.
2. **Tag the variable with a rotation comment**: `// rotated YYYY-MM-DD, next rotation YYYY-MM-DD`. The comment is enough to defuse the audit finding in future re-scans and demonstrates rotation discipline to the buyer.
3. **Plan the env-to-vault migration** as a Day-30-post-close item if the buyer is large enough to operate a real secrets manager. Pre-close, the comment + abstraction layer are sufficient.

## How the seller could have prevented this

This finding is not a bug. It is a pattern that compounds with codebase age. The fix is to introduce a `KeyManager` abstraction before the third place in the codebase that needs to read an encryption key. By the audit timing (typically Year 3+ for an indie SaaS exit), the pattern is usually already established and ten or twenty call sites have to be refactored.

The cheap version: add a single comment to each `encryptionKey =` assignment recording when it was last rotated. The audit will downgrade the finding to LOW or INFO and the buyer's DD lead will move on.
