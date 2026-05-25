---
finding_category: credentials
severity_observed: high
remediation_effort: M
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# Six committed .env files containing 23 high-severity secrets

## What the audit found

A PHP + JavaScript codebase, roughly 367k LOC, infrastructure-tooling category. The credential-inventory specialist found 38 credential findings across the tree, 23 of them HIGH severity, spread across six `.env` files that had been committed to the repository at various points in its history.

The files were not in the current working tree (the team had eventually added them to `.gitignore` and `git rm --cached`'d them), but they remained reachable through `git log -p`. Several of the secrets had never been rotated after the original commit.

## How the audit caught it

Deterministic, two-stage.

Stage one: walk the working tree for any `.env`, `.env.*`, or `*.env.local` file. Flag each one.

Stage two: walk `git log --all --diff-filter=A --name-only -- '*.env*'` to find every `.env`-pattern file that has ever been added to the repo, even if it has since been deleted. Cross-reference each path against current secret-scanning rules to estimate severity.

Both passes are deterministic. The LLM is only invoked later to write the per-finding human summary if the customer wants the narrative version.

## Why it matters to a buyer

A `.env` file in `git log` is a credential leak that lasts forever, even after the file is deleted from `HEAD`. Anyone who clones the repo can recover the values with three commands. If the secrets in those files are still live, the buyer inherits the breach exposure.

The compounding problem for the buyer is **scope discovery**. The first question after this finding lands is: "for each of these 23 secrets, has it been rotated since the original commit, and if so, when?" The answer is almost always "we don't know without looking, and looking will take a week." That week of investigation either pushes close or transfers the cost to the buyer's first month post-close. Either way, the seller loses leverage.

A second compounding problem: insurance. Reps and warranties insurers ask explicitly whether any credentials are in source control. A "no" that turns out to be "yes" voids the policy.

## Recommended remediation

Pre-close, in priority order:

1. **Rotate every credential that has ever appeared in a committed `.env`,** regardless of whether it is currently in the working tree. Treat this as a security-incident playbook, not a chore. Document the rotation date for each secret in a single CSV the data room can reference.
2. **Add a pre-commit hook (e.g. `gitleaks`, `detect-secrets`)** that blocks commits introducing `.env`-pattern files. This must ship before the audit re-scan if the audit is being run twice.
3. **Move all secrets to a managed secrets store** (1Password, Doppler, AWS Secrets Manager, Vault). The buyer will require this on Day 1 post-close anyway; doing it pre-close converts a buyer-side cost into a seller-side closing strength.
4. **Optionally, rewrite history** with `git filter-repo` to remove the `.env` files from the git log entirely. This is controversial (it breaks every existing clone and every existing fork) but it is the only true remediation. If the team chooses not to do this, the data-room note has to say so explicitly.

## How the seller could have prevented this

A pre-commit hook on Day 1 of the repo. Total cost: 10 minutes of setup, $0 in tooling. Total value at exit: the difference between a clean credential-inventory health score and a 0/100 score, which we have seen quoted as five to seven figures in valuation depending on the size of the deal.

The pattern across audits is that founders know `.env` files should not be committed and commit them anyway under deadline pressure. The fix is mechanical (a hook), not behavioral (a reminder).
