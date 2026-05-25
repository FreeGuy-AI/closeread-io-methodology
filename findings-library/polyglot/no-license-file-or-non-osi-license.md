---
finding_category: ip_ownership
severity_observed: high
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 4/10 incidence)
---

# No LICENSE file or non-OSI-approved license

## What the audit found

Four audits in the batch of ten had either no `LICENSE` file at the repository root or a license that did not match any OSI-approved SPDX identifier. The breakdown was two repos with no license file at all, one repo with a `LICENSE` file containing "All rights reserved" boilerplate, and one repo with a hand-written custom license that included a non-compete clause and a revenue-sharing trigger.

Three of the four were on GitHub with the OSS-style "fork me" pitch in the README. Two had external contributors merged into `main`. One had a paying commercial customer reading the repo under the assumption that "it's on GitHub, it must be OSS."

For an OSS project, no license is a contradiction in terms. Without an explicit grant, copyright reverts to the author and every consumer is technically infringing. For a commercial SaaS being sold, the absence of a clear license between the seller and any contributors creates an IP ownership ambiguity that M&A counsel will catch in week one of diligence.

## How the audit caught it

Deterministic. The license_posture specialist walks the repository root for the canonical file names:

```
LICENSE
LICENSE.md
LICENSE.txt
COPYING
COPYING.md
```

If a file exists, the specialist hashes it and matches against the SPDX license-list-data corpus. An exact match emits an INFO finding with the SPDX ID. A near-match (above 95% similarity) emits a LOW finding suggesting the maintainer adopt the canonical text. No match emits a HIGH finding flagging the license as custom or non-standard.

Absence of any license file emits a HIGH finding directly. The specialist also walks the `package.json`, `pyproject.toml`, and equivalents for a declared `license` field and cross-references against the file on disk. Mismatches (file says MIT, manifest says Apache-2.0) emit a separate MEDIUM finding for contributor confusion.

## Why it matters to a buyer

The buyer's M&A counsel will require, before close, written assignment of rights from every person who has ever committed to the repository, OR a clear OSI-approved license that grants the buyer the right to use, modify, and relicense the code. Without either, the deal stalls.

The cost depends on the contributor history. For a solo-author repo with no outside contributors, the seller signs an assignment in an hour and the cost is zero. For a repo with 50 contributors over five years, the seller has to track down every contributor, get each one to sign a Contributor License Agreement (CLA) or Developer Certificate of Origin (DCO) retroactively, and document the chain of custody. Contributors who have left the industry, changed email addresses, or refused to sign create gaps that counsel cannot close.

The realistic worst case in the batch was the custom-license repo with the non-compete clause. The buyer's counsel flagged the clause as potentially binding on the acquirer post-close, which would have prevented the buyer's parent company from operating in an adjacent market. The deal restructured around an indemnification provision that effectively reduced the deal value by 8%.

The base case for the absence-of-license repos is simpler: a 30-day delay while CLAs get gathered, plus a price discount in the range of 2-5% for the IP risk that cannot be fully closed.

## Recommended remediation

In order, with no skips:

1. **Pick a license.** For permissive grants with no patent concerns, MIT. For permissive with explicit patent grants, Apache-2.0. For copyleft with network-use clauses, AGPL-3.0. For dual-licensing strategies, MIT-or-commercial.
2. **Add the canonical text as `LICENSE` at the repo root.** Copy from `https://spdx.org/licenses/` to ensure exact match against the SPDX corpus. Add the year and copyright holder.
3. **Declare the license in the manifest.** `"license": "MIT"` in `package.json`, `license = "MIT"` in `pyproject.toml`, equivalent in each ecosystem's manifest format.
4. **For past contributors, send a CLA or DCO retroactively.** Use a service like CLA Assistant or the Linux Foundation's DCO bot for new commits. For historical commits, a one-time email to each contributor with the assignment language is the standard path.
5. **For repos that shipped under a custom license,** consult counsel before relicensing. Some custom clauses bind downstream consumers and cannot be unwound without their explicit consent.

## How the seller could have prevented this

The structural prevention is to include `LICENSE` in the new-repo template, with the chosen SPDX-identified text and the year populated automatically. Every new repo starts compliant. The seller never has to think about it.

The behavioral prevention is to require a DCO sign-off on every PR via a bot that blocks the merge if the sign-off is absent. This builds the IP chain of custody as a side effect of every commit. By the time the seller is at exit, every contribution has a documented assignment and counsel has nothing to gather.

The seller who has done neither faces the slow contributor-tracking work in the weeks before close, against the deal-clock pressure of a buyer who will not close until the IP chain is clean. The seller who has done both arrives at exit with a license_posture finding that reads "MIT, declared in manifest, DCO sign-off on 100% of commits," and one fewer reason for the buyer to ask for a discount or a delay.
