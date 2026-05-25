---
finding_category: ip_ownership
severity_observed: medium
remediation_effort: M
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# Strong-copyleft repo license with zero per-file SPDX or copyright headers

## What the audit found

Two audits in the same batch declared a strong-copyleft license (AGPL-3.0) at the repository root via `LICENSE` file, but the IP-ownership specialist's per-file scan returned **zero source files with SPDX-License-Identifier headers or copyright headers**.

Both were TypeScript codebases, both above 250k LOC, both in categories where the AGPL choice was intentional (the founders had explicit dual-license commercial strategies). Neither codebase had the per-file metadata that the license operationally requires for clean enforcement.

## How the audit caught it

Deterministic. Two parallel scans:

1. Repo-level: read `LICENSE` (and `COPYING`, `LICENSE.md`, etc.) and classify the declared license via SPDX matching.
2. Per-file: walk source files (currently `.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.go`, `.rb`, `.php`, `.java`, `.rs`) and grep the first 30 lines of each for `SPDX-License-Identifier`, `Copyright (c)`, or `Copyright (C)` patterns. Compute ratio.

A finding fires when the repo declares a license (especially a strong-copyleft one) and the per-file ratio is below 5%. The audit health score on this artifact maxes out at 20/100 in this case, regardless of how clean the rest of the IP posture is.

## Why it matters to a buyer

Three problems compound here.

**Enforcement.** The AGPL's copyleft trigger is on distribution. Without per-file headers, a downstream user who incorporates a single source file (legally or not) into their product has a much weaker case against them, and the seller has a much weaker case for them. The license is at the repo level; the violations happen at the file level.

**Contributor IP chain.** Without per-file copyright headers, the chain of who contributed which lines under what license is not visible in the source. The audit cannot confirm the rep "all contributors have assigned IP to the company" because the source itself does not record contributor identity at the file level.

**Dual-license confusion.** Both sellers in this batch had commercial-license arrangements ("AGPL for OSS users, paid commercial license for enterprise"). Without per-file headers, an enterprise customer who has signed the commercial license has no way to verify (from the source they were licensed) which terms apply. The buyer inherits this contractual ambiguity at close.

## Recommended remediation

Pre-close:

1. **Add SPDX-License-Identifier headers to every source file.** A single script: walk the source tree, prepend a 2-line comment block matching the file's comment style. One afternoon for a 250k LOC codebase. Free tools: `reuse` (REUSE.software), `licenseheaders`, custom Node/Python script.
2. **Add copyright headers** that name the legal entity that owns the IP (typically the company, not the founder).
3. **For dual-licensed codebases, add a CONTRIBUTING.md note** explaining the CLA or DCO process and a `COMMERCIAL-LICENSE.md` summarizing the alternate terms.
4. **For dependencies under non-permissive licenses** (GPL, AGPL, SSPL), document each one in the data room with the rationale for the dependency and the chosen interaction model (linking vs. modification vs. distribution).

## How the seller could have prevented this

The choice to ship the LICENSE file at the repo root and skip per-file headers is the default behavior of every "init a new repo" CLI (`git init`, `npm init`, `create-next-app`, etc.). None of them prompt for per-file headers, and the cost of going back to add them grows linearly with the source tree.

The structural prevention is a pre-commit hook on Day 1 that requires a SPDX header on every new source file. Tooling: `pre-commit` with `reuse` or with a custom shell script. Total cost: 30 minutes of setup. Total value at exit: a 100/100 IP-ownership health score instead of a 20/100 one, which is a substantive valuation input for any acquirer in a regulated or enterprise-sales market.
