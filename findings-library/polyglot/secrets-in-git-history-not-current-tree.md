---
finding_category: credentials
severity_observed: high
remediation_effort: M
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 5/10 incidence)
---

# Credential present in git history but absent from current tree

## What the audit found

Five audits in the same batch of ten. Different stacks, different team sizes, different commit cadences. The same pattern in every one: the credentials specialist's history walk surfaced a secret (API key, database connection string, OAuth client secret, signing key) that had been removed from the current `HEAD` but still lived in a prior commit reachable by any clone of the repository.

The specifics varied:

- One repo had an AWS access key pair committed to `config/development.yml` in 2023, removed via a normal `git rm` in 2024, and rotated at the AWS console at the same time. The seller believed the rotation closed the exposure. The audit found the original key pair in commit `a3f7c1d` from 2023, still recoverable to anyone who ran `git show`.
- One repo had a production PostgreSQL connection string (host, port, database, username, password) committed to a `docker-compose.prod.yml` file in 2022, removed in 2023 when the team migrated to environment variables. The database password had never been rotated.
- One repo had a Stripe live secret key briefly committed to a `.env` file in 2024, noticed by the founder within an hour, removed in the next commit. The founder did not rotate the key because "no one would have cloned the repo in that hour." The audit found the key in the dangling commit and verified it was still active by querying Stripe's `/v1/account` endpoint with the key.
- One repo had a Twilio auth token committed to a test fixture in 2021, removed during a routine cleanup in 2022, and the seller had no memory of the incident. The audit recovered the token from history; a separate operational check confirmed the token was still valid against the Twilio API in 2026.
- One repo had a GitHub personal access token (PAT) with `repo` scope committed to a CI configuration file in 2023, removed when the team migrated to GitHub Actions OIDC in 2024. The PAT was never revoked at the GitHub user-settings level.

In four of the five cases, the original credential was still valid against the upstream service at the time of audit. In the fifth, the credential had been rotated correctly, but the history still leaked the historical credential pattern to anyone analyzing the repository for credential hygiene.

## How the audit caught it

The credentials specialist runs three checks in sequence. The history check is the one that catches this finding.

```
git log --all --full-history --diff-filter=D --pretty=format:'%H' -- '*' \
  | xargs -I{} git show --pretty=format: {} \
  | grep -E '(AKIA[0-9A-Z]{16}|sk_live_[0-9a-zA-Z]{24,}|ghp_[0-9a-zA-Z]{36}|...)' 
```

The actual implementation uses the `gitleaks` or `trufflehog` toolchain with a curated rule set covering 60+ credential patterns (AWS, GCP, Azure, Stripe, GitHub, GitLab, Twilio, SendGrid, Slack, Datadog, generic high-entropy strings flagged by Shannon entropy).

A HIGH finding fires whenever a credential pattern matches in any commit reachable from any branch or tag, even if `HEAD` is clean. A CRITICAL finding fires whenever the recovered credential, when probed with a single read-only API call (`/v1/account`, `/user`, `/me`, depending on the service), responds with a 2xx status code, confirming the credential is still valid.

The history walk is expensive on large repositories (it traverses every commit and every blob), so it runs only on deep audits. The shallow audit catches credentials in `HEAD`; the deep audit catches the historical leaks.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the rotation gap. The credential is still recoverable by every party who has ever cloned the repository: every current team member, every former team member, every contractor, every CI cache, every developer laptop, every backup, every fork. Removing the secret from `HEAD` does not remove it from any of those places. The seller who believes "I rotated and removed it" has done half the work; the other half is rewriting history and rotating again under the assumption that the historical credential is compromised.

Second, the trust signal. A historical credential leak is one of the cleanest signals a buyer has that the seller's security culture treats incident response as cleanup rather than containment. The right response to a leaked credential is rotate-immediately and then rewrite-history. The wrong response is rewrite-history-without-rotating, or rotate-without-rewriting-history, or do-nothing-because-no-one-noticed. Every one of those wrong responses leaves the credential exposed in a way the seller cannot see and the buyer's diligence team can.

Third, the compounding-with-time risk. Every additional year the historical credential sits in the repository is another year of cumulative exposure: more forks created, more clones made, more backups stored, more former team members who still have local copies. A credential leaked in 2021 and discovered in 2026 has been recoverable for five years. The seller cannot know who has it. Realistic dollar impact for a proper remediation: $5K to $15K of engineering work for the history rewrite, plus the cost of rotating every credential ever leaked, plus the downstream cost of reissuing tokens to every consumer of those credentials.

## Recommended remediation

In order, all of these need to happen:

1. **Treat every historical credential as compromised.** Do not investigate whether the credential "was actually used by anyone bad." Assume it was. Rotate every API key, database password, signing secret, OAuth client secret, and access token whose value appeared in any historical commit.
2. **Rewrite the history.** Use `git filter-repo` (preferred over the deprecated `git filter-branch`) or BFG Repo-Cleaner to remove the credential from every past commit. The tool walks every blob, replaces matching patterns with placeholders, and produces a new history with the credential genuinely gone.
3. **Force-push to every remote.** Every fork, every mirror, every backup must receive the rewritten history. This is the step that requires coordination: every active collaborator will have to delete their local clone and re-clone, because their local history still contains the credential. Notify the team before the force-push, not after.
4. **Invalidate every old clone you cannot reach.** For repositories with many forks (open-source projects, popular templates), accept that some forks will never receive the rewritten history. The credential rotation in step 1 is the only defense for those clones. The history rewrite reduces future exposure; it does not undo past exposure.
5. **Install a pre-commit hook.** Use `gitleaks`, `detect-secrets`, or `trufflehog` so any future attempt to commit a credential-shaped value fails before it reaches the remote. This is the same prevention recommended for the live `.env` finding; the same hook catches both classes of leak.

## How the seller could have prevented this

The structural prevention is a CI gitleaks scan that runs on every push and rejects the merge if a credential pattern matches. The scan catches the leak at PR time, before the offending commit ever lands on a long-lived branch. The seller never needs to run a history rewrite because the leak never reaches `HEAD`.

The behavioral prevention, for teams without CI scanning, is a habit of scrutinizing every commit that touches a configuration file, a CI script, or a `.env*` variant. This works for small disciplined teams and fails reliably for everyone else.

The seller who has done neither and now discovers a historical leak in the data room has only the full remediation path: rotate everything, rewrite the history, force-push to every remote, reissue tokens to every downstream consumer, document the incident in the data room. The remediation usually takes one to two engineering weeks and produces a documented incident the buyer will price into the deal. The seller who has done the structural prevention arrives at exit with a clean history finding and one fewer credentials concern to negotiate.
