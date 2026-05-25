---
finding_category: test_coverage
severity_observed: high
remediation_effort: L
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; observed across multiple stacks)
---

# Test coverage below 30% of source LOC on a non-trivial codebase

## What the audit found

Several audits in the batch surfaced test coverage below 30% on codebases larger than 10,000 LOC. The pattern was consistent across stacks: the test suite existed, the canonical test framework was wired (pytest, jest, rspec, gotest), and CI ran the suite on PRs. But the line-coverage measurement showed under one-third of the production code was actually exercised by any test.

The most common shape: a strong unit-test layer for the model layer (database models, pure functions) plus an integration-test layer for the API surface, with nothing in between. The middle layer (business-logic services, request handlers, async tasks) ran to production untested and constituted the bulk of the codebase by line count.

This is the structural failure mode of "tests are for the parts that are easy to test." The buyer reads the coverage number, not the test-strategy narrative.

## How the audit caught it

Deterministic. The test-coverage specialist detects the canonical test framework from manifest dependencies, runs the language's coverage tool (coverage.py for Python, jest --coverage for JS, simplecov for Ruby, go test -cover for Go), and captures the line coverage percentage per file plus overall.

A coverage measurement below 30% on a codebase larger than 10,000 LOC emits a HIGH finding. Below 10% on the same threshold emits CRITICAL.

The artifact also emits a test-surface-alignment finding if the fraction of source files with a corresponding test file is below 30% (heuristic: src/X.py paired with tests/test_X.py).

## Why it matters to a buyer

A buyer reading a 25% coverage number on a 50,000-LOC codebase concludes: "if I touch anything in the 75% uncovered, I will not know I broke production until a customer complains." The implication for their post-close engineering velocity is severe. Refactoring becomes risk; feature work becomes risk; even fixing the previously-surfaced security findings becomes risk.

The dollar impact is a tax on the first 90 days post-close. Buyer's engineering team budgets a 2-3x slowdown on any work that touches uncovered code. That slowdown is real cost; the seller sees it as a deal discount.

The cultural impact is harder to price but real: a codebase with low coverage signals that the seller's team did not invest in maintainability. Buyer's M&A counsel reads this as a sophistication signal that affects the negotiation tone, not just the price.

## Recommended remediation

A seller cannot get from 25% to 75% coverage in two weeks. The remediation that actually works pre-listing is targeted rather than comprehensive:

1. **Identify the top 20 highest-traffic code paths** (request handlers for the most-used endpoints, async tasks for the highest-revenue features). These get 20-30 tests each, covering happy-path + 2-3 known failure modes. Three calendar weeks of focused work.
2. **Add CI coverage enforcement at the current percentage** (so coverage cannot regress further before listing). Most CI systems support this in 1-2 lines.
3. **Document the coverage strategy** in the data room: which code paths are intentionally untested (UI rendering, generated code, vendored dependencies) and why. The narrative beats the bare number.
4. **Set a 12-month post-close coverage growth target** the buyer can include in their post-close roadmap (e.g. "30% to 60% over 12 months at X engineer-hours/month").

A seller who hands a buyer a 30% coverage number + a written strategy + a 12-month growth target is in a materially better position than a seller who hands the bare number with no context. The strategy is the move.

## How the seller could have prevented this

The structural prevention is "test-first discipline from day one," which is rarely realistic for a solo or 2-person team optimizing for shipping velocity in years 1-2. By year 3 the test debt is structural.

The realistic prevention: monthly coverage measurement during the build phase + a rule that no PR may decrease coverage. This does not guarantee high absolute coverage but prevents the silent decline.

## When the 30% threshold might be the WRONG bar

Some codebases have coverage measurements that under-report by design:

- **UI-heavy React / Vue codebases** where the rendering layer is intentionally tested via end-to-end tools (Cypress, Playwright) that don't show up in the line-coverage number.
- **Generated-code repos** (protobuf stubs, OpenAPI clients) where 60% of the source tree is auto-generated and excluded from coverage targets.
- **Notebooks / data-science codebases** where the canonical testing pattern is "run the notebook and inspect outputs," not unit tests.

In these cases the artifact emits the finding but the seller can rebut it in the packet narrative with a clear coverage-strategy statement. The buyer's reading of "30%" with strategy context is different from "30%" without it.

## Related findings

- [single-author-100-percent-commit-share.md](single-author-100-percent-commit-share.md): single-author codebases often have low test coverage because the author can hold the system in their head; the redundant signal compounds.
- The reliability methodology page (02) covers the failure-path-test-quality dimension that complements raw coverage volume.
- The security methodology page (08) covers the cross-reference where low coverage amplifies post-SAST regression risk.
