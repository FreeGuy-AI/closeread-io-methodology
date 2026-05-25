---
finding_category: test_coverage
severity_observed: high
remediation_effort: XL
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# Zero test files detected across a quarter-million-line production codebase

## What the audit found

A TypeScript codebase, roughly 258k lines across 1,528 source files, indie SaaS in document-handling category. The test-coverage specialist scanned for the usual signals: a `test/`, `tests/`, `__tests__/`, or `spec/` directory; test runner configs (`jest.config.*`, `vitest.config.*`, `playwright.config.*`); and source-file naming patterns (`*.test.ts`, `*.spec.ts`).

It found none of them. Zero test files. Zero test directories. Zero coverage configs.

## How the audit caught it

Deterministic. Three parallel scans: a path walk for test directories, a glob match for runner configs at the repo root and at each workspace root in a monorepo, and a regex pass over source filenames for `.test.` and `.spec.` infixes. The specialist flags HIGH if all three return empty against a source-file count above a threshold (currently 200 files; arbitrary but useful).

The finding is structural, not semantic. The audit does not assert that the code is buggy. It asserts that the engineering org has no automated way to discover that it is.

## Why it matters to a buyer

This is the single largest operating-risk signal a buyer's technical DD will surface from a quick scan of the repo. It is the first thing every acquisition-side engineer asks about in the first hour of diligence, ahead of architecture, ahead of dependencies, ahead of security.

The buyer's read is:

1. **Velocity collapse post-close is near-certain.** Any non-trivial refactor in a zero-test codebase becomes an open-ended manual QA exercise. Engineering velocity post-close runs 30% to 60% of the seller's claimed pre-close pace, depending on stack complexity. This is the modal post-close surprise.
2. **The next outage is unforecastable.** Without regression tests, every production incident has to be reverse-engineered from logs. Mean time to recovery on incidents that touch the changed module typically doubles.
3. **The first integration with the buyer's existing stack will be brutal.** Buyer's engineers cannot safely modify any of the seller's code without writing tests first, which adds weeks to the integration plan and erodes the deal's expected synergy capture.

Buyer's valuation models adjust by 10% to 25% for this single finding. The seller often does not know.

## Recommended remediation

This is an XL effort and cannot be backfilled in the gap between LOI and close. The path that actually works:

1. **Acknowledge in the data room.** Do not try to hide it. Buyers find it in the first afternoon. Acknowledging it converts a discovery into a known and priced item.
2. **Ship a test scaffolding PR before going to market.** Add Vitest or Jest, configure a coverage runner, and write tests for the three modules a buyer's engineer is most likely to touch first (payment integration, auth, primary data model). Total effort is two weeks of one senior engineer's time. The buyer reads this as "the seller knows the gap and is closing it," not as "the seller is in denial."
3. **Add a CI gate on patch-level coverage growth.** Even a gate that just requires coverage to be non-decreasing on new PRs is enough to demonstrate that the trajectory has flipped.

## How the seller could have prevented this

The day-one decision to skip tests at founding is rational. The day-365 decision to still have zero tests is the one that costs valuation.

The single highest-leverage prevention is a CI line that fails the build if a new module is added without at least one test file. Every codebase that has shipped this guardrail in its first 90 days arrives at exit with a test-coverage health score in the 70 to 95 range. Every codebase that has not arrives with a score below 40, regardless of engineering team size or seniority.
