---
finding_category: credentials
severity_observed: critical
remediation_effort: M
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 7/10 incidence)
---

# Committed .env file in repository root or production code path

## What the audit found

Seven audits in the same batch of ten. Different stacks (Node/TS, Python, PHP, Go, polyglot), different team sizes, different commit cadences. The same pattern in every one: a `.env` file (sometimes `.env.example`, sometimes `.env.local`, sometimes the bare `.env`) sitting in the repository, tracked by git, visible to anyone with read access.

The contents varied by repo:

- Some were placeholders, `KEY=YOUR_KEY_HERE` style, harmless on their own but signaling weak hygiene as a baseline.
- Some shipped "development defaults" that were real credentials someone decided were low-risk enough to commit. They usually aren't.
- Some had values that started as scaffolding, never got rotated, and were still valid against production systems at audit time.
- One (a TypeScript document-signing platform in this batch) had a CRITICAL real secret sitting in the committed history. The seller had removed it from `HEAD` months earlier but never rewrote the history, so the secret was still recoverable by anyone who cloned the repo.

## How the audit caught it

The credentials specialist is path-based first, content-based second.

The path check fires a HIGH finding whenever any tracked file matches `.env` or `.env.*` (excluding `.env.example` only when it lives alongside a `.gitignore` rule that excludes everything else, which is rare). The content check then walks the file with the standard credential regex set (AWS access keys, Stripe keys, Bearer tokens, GitHub PATs, generic high-entropy `KEY=...` patterns) and stacks an additional CRITICAL finding for every match.

The history check is the expensive one and runs only on a deep audit: `git log --all --full-history -- '.env*'` returns every commit that ever touched a `.env*` file. Any blob found in history that matches the credential regex set gets flagged CRITICAL even if the current `HEAD` is clean. This is how the Documenso case surfaced.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the cultural signal. A committed `.env` is a documented finding in any SOC2 or ISO 27001 readiness review. It tells a buyer that the seller's security baseline is below the line required for enterprise contracts, and that the first 90 days post-close will include credential hygiene remediation work that should have been done years earlier.

Second, the operational risk. A `.env.example` shipped with real-looking defaults often does get used in production by an operator who never read the docs. The credential that was "just for dev" becomes the credential that runs payments, sends emails, and signs JWTs in the live system.

Third, the history is forever. Rotating a leaked credential after acquisition closes the live exposure, but the historical commit is still in every fork, every clone, every CI cache, every developer laptop that ever pulled the repo. Realistic dollar impact for a proper remediation: $5K to $15K of post-close engineering work to do a `git filter-repo` or BFG history rewrite, rotate every credential that ever appeared, reissue tokens to every downstream consumer, and force-push the rewritten history to every remote.

## Recommended remediation

In order, all of these need to happen:

1. **Stop the bleeding.** Add `.env` and the common variants to `.gitignore`. Run `git rm --cached .env` (and each variant) to untrack without deleting locally. Commit. The repo no longer accepts new versions of the file.
2. **Rotate every credential that was ever in the file.** Assume compromise from the day of the first commit. This includes API keys, database passwords, signing secrets, OAuth client secrets, and any token whose value appeared even once.
3. **Rewrite the history.** Use `git filter-repo` (preferred) or BFG Repo-Cleaner to remove the file from every past commit. Force-push to every remote. Notify every collaborator that they must re-clone, because their local history still contains the secret.
4. **Replace with a placeholder pattern.** Add `.env.example` containing only `KEY=PLACEHOLDER` patterns, never real values. Document the required variables in a README so a new operator can populate `.env` from the example without guessing.
5. **Install a pre-commit hook.** Use `gitleaks` or `detect-secrets` so any future attempt to commit a credential-shaped value fails before it reaches the remote.

## How the seller could have prevented this

The structural prevention is to never let it happen in the first place: every new repo initialized from a template that has `.env*` in `.gitignore` by default, an `env.example` (no leading dot) documenting required variables without committing values, and a secrets manager (Vault, AWS Secrets Manager, Doppler, 1Password) handling staging and production credentials from day one.

The behavioral prevention, for a team that already has the structural pieces in place, is a CI gitleaks scan on every push. The first regression surfaces as a failed build, not as an audit finding three years later in a data room.

The seller who has done neither faces the full remediation work in the weeks before close, against a buyer who will read the audit report and price the risk into the deal whether the seller remediates or not. The seller who has done both arrives at exit with a clean credentials finding and one fewer reason for the buyer to ask for a discount.
