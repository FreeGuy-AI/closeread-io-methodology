---
finding_category: security
severity_observed: medium
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 8/10 incidence)
---

# Missing SECURITY.md and no documented vulnerability disclosure policy

## What the audit found

Eight of ten audits in the batch had no `SECURITY.md` file at the repository root and no documented vulnerability disclosure policy anywhere in the project. A security researcher who finds a CVE in any of these projects has no published path to report it responsibly. The choices are open a public GitHub issue (which discloses the vulnerability before the maintainer can patch), tweet at the maintainer (same problem, larger audience), or do nothing.

The batch crossed every stack and every team size. Two repos had over a thousand stars and an active issue tracker. Six had at least one paying customer in production. None of them had a 30-minute file that costs nothing to write and would have closed the gap entirely.

In one case, the maintainer had a `security@` email in their personal blog footer but nowhere in the repo. A researcher who hits the repo first will not find it.

## How the audit caught it

Deterministic. The security specialist walks the repository root and the two GitHub-recommended fallback paths for the canonical file name:

```
SECURITY.md
.github/SECURITY.md
docs/SECURITY.md
```

Absence emits a MEDIUM finding. Presence triggers a content check that looks for a reporting email or URL, an acknowledgment commitment, and an optional PGP key. A file that exists but contains only a placeholder or a broken contact gets downgraded to LOW (still a finding, but the file is there to fix rather than to create from scratch).

The specialist also checks whether the repository has GitHub's private vulnerability reporting feature enabled via the GitHub API. Enabled-but-no-file is rare and gets a separate INFO finding suggesting the maintainer document the channel.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the cultural signal. A buyer running diligence will check for `SECURITY.md` as a baseline hygiene marker. Absence is a soft flag. It tells the buyer that the seller has not thought about disclosure, which usually correlates with not having thought about incident response, key rotation, or downstream notification either. The audit cannot prove any of those gaps from `SECURITY.md` alone, but the absence raises the probability that the gaps exist.

Second, the operational risk. Post-close, the buyer inherits responsibility for any zero-day reported through public channels. If a researcher opens a public GitHub issue describing a critical CVE on day three of the buyer's ownership, the fire drill that follows is the buyer's. The buyer has to triage, patch, notify customers, and manage the public disclosure timeline, all without the muscle memory of having done it before in this codebase.

Third, the regulatory cost. Enterprise customers increasingly require their vendors to have a documented vulnerability disclosure policy. SOC2 and ISO 27001 readiness reviews flag the absence. A buyer planning to move the acquired product upmarket will need to add `SECURITY.md` before the first enterprise deal closes anyway. Doing it pre-close is free. Doing it post-close as part of an enterprise sales motion is a 30-minute fix that delays a six-figure deal by a week.

## Recommended remediation

The fix is 30 minutes:

1. **Copy GitHub's `SECURITY.md` template** from `https://github.com/github/.github/blob/main/SECURITY.md` and customize the supported-versions table for the project.
2. **Add a reporting `mailto:`** at a domain the maintainer controls. Avoid personal email addresses; a `security@` alias on the project domain is the right call.
3. **Optionally publish a PGP public key** for sensitive reports. Not required, but useful for higher-trust researchers.
4. **Enable GitHub's private vulnerability reporting** under repo Settings, Security, Advisories. This gives researchers a one-click in-platform path that does not require email.
5. **Commit `SECURITY.md` at the repo root.** GitHub will render a "Security" tab automatically and surface the policy on the repo home page.

## How the seller could have prevented this

The structural prevention is to include `SECURITY.md` in the new-repo template. Every new repo starts with the policy in place, the contact populated, and the disclosure channel configured. The seller never has to think about it again.

The behavioral prevention is a release checklist that includes "verify SECURITY.md exists and contact is current." Slower, more error-prone, but works for a team that has not yet built out templates.

The seller who has done neither faces a 30-minute fix in the weeks before close, with the awkwardness of explaining to the buyer why a basic security artifact was missing from a project with paying customers. The seller who has done either arrives at exit with one fewer soft flag in the buyer's diligence report and one fewer story to tell about why the security baseline is healthier than the missing artifact suggested.
