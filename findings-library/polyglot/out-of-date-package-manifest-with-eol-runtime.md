---
finding_category: stack_hireability
severity_observed: high
remediation_effort: L
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 4/10 incidence)
---

# Out-of-date package manifest pinning an end-of-life runtime

## What the audit found

Four audits in the same batch of ten. Different languages (two Python, one Node, one Ruby), different vintages (one greenfield from 2024, three legacy systems older than five years). Same pattern in every one: the package manifest at the root of the repository pinned a language runtime version whose upstream maintainers had stopped publishing security patches.

The specifics varied:

- One `pyproject.toml` required `python = "^3.9"` against a Python 3.9 line whose upstream end-of-life was October 2025. The repo last touched the version constraint in 2022 and never revisited it.
- One `package.json` set `"engines": { "node": "16.x" }` against a Node 16 line whose upstream end-of-life was September 2023. The CI was still building on Node 16 because the constraint pinned it there.
- One `Gemfile` declared `ruby "2.7.6"` against a Ruby 2.7 line whose upstream end-of-life was March 2023. The deployed application was running on a Heroku stack whose security patches for 2.7 ended at the same time.
- One `pyproject.toml` allowed Python 3.8 (`python = ">=3.8"`) against a Python 3.8 line whose upstream end-of-life was October 2024. The repo's actual runtime in production was 3.11, but the constraint advertised the older floor to anyone reading the manifest.

In every case the manifest was the authoritative document a buyer's diligence team read first to assess platform health.

## How the audit caught it

The stack hireability specialist parses the manifest at audit time and looks up each declared runtime version against the maintained EOL table for that language. The lookup table is refreshed monthly from the upstream sources (`endoflife.date`, the Node release schedule, the Python developer guide, the Ruby maintenance branches page).

A HIGH finding fires whenever the lowest version permitted by the constraint is past its upstream EOL date as of the audit run. A MEDIUM finding fires whenever the lowest permitted version will hit EOL within 90 days. The detection is deterministic: no fuzzy matching, no inference, just the parsed constraint against a known date.

The reliability specialist cross-references the same data: an EOL runtime cannot receive upstream security patches, so any CVE published against that version after EOL is effectively a permanent vulnerability. This often stacks the same repository with two findings from two specialists pointing at the same root cause.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the security posture. A runtime past EOL cannot receive upstream patches. Any CVE published against it after the EOL date is a vulnerability the seller cannot fix without a runtime upgrade. The buyer inherits the full cost of that upgrade plus the risk window between close and upgrade completion.

Second, the hiring pool. Engineers who want to work on a modern stack do not want to maintain code pinned to Python 3.9 or Node 16. The seller is signaling to every prospective hire that the codebase has not kept pace with the language's evolution. This compounds the key-person risk: the founder who is comfortable on the old version is the only one who will stay.

Third, the migration debt. The longer the constraint sits past EOL, the harder the eventual upgrade becomes. A two-version jump (3.9 to 3.11) is usually a weekend of work. A four-version jump (3.9 to 3.13 after sitting on 3.9 for three more years) often involves dependency churn, breaking API changes in libraries the seller never tracked, and test suite rewrites. Realistic dollar impact for a delayed runtime migration: $10K to $40K of post-close engineering work, depending on the dependency tree.

## Recommended remediation

In order, all of these need to happen:

1. **Identify the gap.** Pull the EOL date for the currently-pinned floor from `endoflife.date` or the upstream maintenance page. Pull the EOL date for the language's current stable line. Calculate the version distance you need to close.
2. **Run the upgrade locally on a branch.** Bump the manifest to the current stable line. Run the full test suite, fix every breakage, document any dependency that needs to be replaced because it dropped support for the old version.
3. **Update CI to the new runtime.** Replace the matrix entries that pin EOL versions. Add a matrix entry for the next stable version so future drift surfaces as a CI failure, not as an audit finding.
4. **Pin a maintained floor in the manifest.** Express the constraint as a range whose lower bound is a currently-supported version, not a historical artifact. For example, `python = "^3.11"` instead of `python = "^3.9"`.
5. **Document the runtime policy.** A short note in the README or CONTRIBUTING file declaring which runtime versions the project supports and how often the floor moves. Six months past the floor's EOL is a reasonable default cadence.

## How the seller could have prevented this

The structural prevention is a quarterly calendar event labeled "review runtime constraints." Three months between checks is short enough that the floor never drifts more than one version past EOL, and the upgrade work stays in the weekend-of-effort range.

The behavioral prevention, for teams already running CI, is a Dependabot or Renovate rule that opens a PR whenever the pinned runtime line approaches EOL. Most teams ignore the PR for the first six months; the prevention works anyway, because the unmerged PR sits in the repository as a visible reminder that the manifest needs attention.

The seller who has done neither faces an awkward conversation in the data room: every buyer who runs even a basic stack audit will surface this finding, and the seller cannot fix it without taking the engineering team off feature work for the days or weeks the upgrade requires. The seller who has done either arrives at exit with a runtime constraint inside the supported window and one fewer reason for the buyer to discount the platform health score.
