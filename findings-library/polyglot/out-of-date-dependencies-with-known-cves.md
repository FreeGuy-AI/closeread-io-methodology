---
finding_category: sca
severity_observed: high
remediation_effort: M
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; HIGH-severity GHSAs in 10/10)
---

# Out-of-date dependencies with known CVEs

## What the audit found

Every audit in the batch surfaced at least one HIGH-severity GHSA against a pinned dependency version. Seven of ten had the same top finding: a `next` package advisory at HIGH severity, on a version one to two majors behind current. The pattern was consistent across stacks: most affected packages sat one to three major versions behind their latest release, and most had public advisories that were six months to two years old.

The distribution across the batch by primary stack was four TypeScript repos, two Python repos, and one JavaScript repo carrying the bulk of the HIGH-severity backlog. The remaining three (one PHP, one Go, one Ruby) had MEDIUM-severity advisories but fewer HIGHs, mostly because their dependency surfaces were smaller.

Several repos had advisories that were already exploited in the wild against other consumers, public PoC code available, and a clear upgrade path. The seller had simply not pulled the upgrade through.

## How the audit caught it

Deterministic. The SCA specialist walks every dependency manifest in the repo (`package.json`, `requirements.txt`, `Pipfile.lock`, `composer.json`, `go.mod`, `Gemfile.lock`, and so on), enumerates the `(ecosystem, package, version)` tuples, and queries OSV.dev for the full advisory set per tuple. Results are stacked by severity, deduplicated across manifests, and emitted as one finding per advisory.

The Day 8 fix landed two reliability changes on top of this baseline: per-manifest isolation (so one malformed lockfile no longer poisons the whole pipeline) and retry-with-backoff on OSV.dev (so a single rate-limited query no longer drops findings silently). Bug 1 in the Day 7 issue log.

## Why it matters to a buyer

Every CVE in a production dependency is a post-close patching tax. The buyer's engineering team inherits the backlog the day the deal closes. A backlog of 50 or more HIGH-severity advisories is usually a full week of dedicated patching work for one engineer in the first 90 days, before they have touched any product roadmap.

The compounding cost is the upgrade chain. A `next` major-version bump usually pulls a TypeScript bump, an ESLint bump, a build-tool bump, and a regression test pass. What looks like one CVE patch on the audit report is often three days of integration work. Multiply that across 50 advisories and the buyer is looking at a quarter of lost velocity.

There is also the cultural signal. A two-year-old HIGH-severity advisory still in the repo is documented evidence that the seller does not have a working dependency-management cadence. The buyer will assume the next two years look the same.

## Recommended remediation

In order of impact:

1. **Rotate keys for any CVE-affected dependency that handles authentication, session state, or signing.** If the advisory describes a key disclosure or signature bypass, assume compromise and rotate before patching.
2. **Patch the HIGH-severity advisories first.** Group by upstream package so one major bump knocks out a cluster. Test each cluster before moving to the next.
3. **Patch the MEDIUM-severity advisories second.** Same pattern.
4. **Install Dependabot or Renovate in CI** with weekly PRs for minors and patches, monthly for majors. The goal is that no advisory older than 90 days ever appears in a future audit.
5. **Set an EOL policy** for the major frameworks (Node, Python, framework majors) that retires versions before upstream support ends.

## How the seller could have prevented this

The structural prevention is Dependabot or Renovate from day one of the repo, configured to open PRs automatically and a maintainer culture of merging them on a weekly cadence. Most teams that do this never see a HIGH-severity advisory older than 30 days in their audit report, because the bot caught it and the team merged the fix before the advisory was ever published.

The behavioral prevention, for a team that has not installed the bot, is a quarterly half-day spent walking the OSV.dev report by hand. Slow, error-prone, and easy to skip when the roadmap is busy. Most teams that rely on this discipline alone end up with the kind of backlog this finding describes.

The seller who has done neither faces a multi-week remediation push in the weeks before close, with the integration risk that comes from upgrading many dependencies at once under deal pressure. The seller who has done both arrives at exit with an SCA finding that reads "zero HIGH-severity advisories, three MEDIUM, all under 60 days old," and one fewer reason for the buyer to ask for a discount.
