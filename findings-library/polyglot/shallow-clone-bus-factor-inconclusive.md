---
finding_category: key_person
severity_observed: info
remediation_effort: XS
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; structural across the batch)
---

# Shallow clone, bus factor inconclusive

## What the audit found

Most of the batch was audited from `git clone --depth 1`. On a shallow clone, the only authors visible to the key-person specialist are the last N committers (typically 1 to 5). Every shallow-cloned target in the batch presented as "single contributor at 100% of commits in the trailing 365-day window," which is the literal observation but a structurally misleading signal.

The pre-Day-8 version of the scanner emitted this as a HIGH single-contributor concentration finding on every audit. A buyer reading the packet would conclude every repo had a bus factor of one, which is almost always wrong. The actual bus factor of a multi-year project with a real contributor history cannot be measured from a shallow clone.

## How the audit caught it

Deterministic. The key-person specialist checks two signals before running its commit-distribution analysis:

1. `.git/shallow` file existence
2. `git rev-parse --is-shallow-repository` return value

If either fires, the scanner emits a single INFO finding (the post-Day-8 fix; landed as Bug 7 in the Day 7 issue log) named "Shallow clone, bus factor inconclusive" with a remediation that asks for either a deep clone or `git fetch --unshallow` and a re-run.

The artifact health stays at 100 because the signal is missing, not bad. The packet still ships, the customer-visible narrative explicitly says the analysis was skipped, and no false-positive HIGH concentration finding gets emitted on what is almost certainly a healthy team.

## Why it matters to a buyer

A buyer running due diligence on a SaaS being acquired needs an answer to "what is the bus factor here, and what is the seller's plan for knowledge continuity post-close?" An INFO "data inconclusive" answer is more honest than a HIGH "single contributor" finding the data does not actually support.

For the seller, this matters because the buyer's M&A counsel will follow up on every HIGH finding. A HIGH concentration finding triggers a round of "we need to talk about your earn-out + retention provisions" conversations. A correct INFO finding triggers a single "please re-share the repo as a full clone" message and the conversation continues normally.

For the audit firm (Closeread or anyone running this methodology), the meta-point is that publishing a structurally-wrong finding is worse than publishing no finding. Honesty at the visible edge is the doctrine (see internal Lesson 021 in the source repo).

## Recommended remediation

The seller should either:

1. **Provide a full-history clone** to the auditor. A modern git repo with 10 years of history is typically under 500 MB; the clone takes a few minutes at most and produces a meaningful bus-factor analysis.
2. **Re-run the audit from a full clone** internally before listing. The seller's own audit packet should have the INFO swapped for a real concentration measurement (whatever it shows). Buyers respond better to a "here is the real number" finding than to a "we did not measure" finding, even if the real number is unflattering.

For internal teams running their own audits with this methodology, set the clone command to `git clone <url>` without `--depth`. Disk and time costs are real but typically rounding error against the audit's overall wall-clock.

## How the seller could have prevented this

Not applicable. This is a tooling caveat, not a finding the seller did anything wrong on. The doctrine is for the auditor to detect and respond honestly, not for the seller to remediate.

## When the INFO finding might be the WRONG answer

If the repo is actually a small, recent, single-author project (a microservice from last month, a side project the seller is selling, an exploratory branch), the scanner has no way to distinguish "shallow clone of a deep repo" from "actually shallow history." In that case the INFO finding is technically correct (the data is inconclusive on the shallow read) but the audit should be re-run with a full clone where the real bus-factor signal is high and the finding upgrades to HIGH.

The doctrine: always prefer to re-run from a full clone. The INFO finding is a placeholder, not a final answer.

## Related findings

- `single-author-100-percent-commit-share.md` covers the case where the signal IS real (deep clone showing actual concentration). The pair is doctrine: "if the data is conclusive, report it; if it is inconclusive, say so explicitly and ask for better data."
