---
finding_category: key_person
severity_observed: medium
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 4/10 incidence)
---

# Monorepo without CODEOWNERS per package

## What the audit found

Four audits in the same batch of ten that ran against a monorepo structure (Nx, Turborepo, pnpm workspaces, Yarn workspaces, Bazel, or a hand-rolled `packages/` layout). The same pattern in every one: a `CODEOWNERS` file existed at the repository root with one or two top-level entries, but no per-package ownership granularity. Every PR routed to the same default reviewer regardless of which package it touched.

The variations were instructive:

- One Nx monorepo had 27 packages under `packages/` and `apps/`. The root `CODEOWNERS` had a single line: `* @founder`. The founder reviewed every PR personally. The audit's bus-factor analysis flagged this as a single-person-dependency disguised as a CODEOWNERS file.
- One Turborepo had 12 apps and 8 internal libraries. The root `CODEOWNERS` listed three reviewers, none of whom mapped to specific packages. Reviewers picked PRs based on Slack pings rather than the CODEOWNERS routing. Two of the three reviewers were one-off contractors who had finished their engagement six months earlier and no longer had merge rights.
- One Bazel monorepo had a hierarchical `OWNERS` convention (Bazel's equivalent of CODEOWNERS) at the top level but no nested `OWNERS` files in the package subtrees. The build system was set up for granular ownership; the team had simply never populated the nested files.
- One pnpm workspaces monorepo had per-package `package.json` files listing maintainers in a custom `"maintainers"` field. The custom field was readable to humans but invisible to GitHub's CODEOWNERS routing. PRs still routed to the root-level default reviewer.

In all four cases the team's mental model of ownership was richer than what the repository actually expressed. The audit's interview pass surfaced "oh, Marie owns the billing package and Theo owns auth" within minutes; the repository encoded none of that knowledge.

## How the audit caught it

The key person specialist runs three passes against monorepo ownership.

The structure pass detects monorepo layouts by checking for `pnpm-workspace.yaml`, `yarn.lock` with `workspaces` in the root `package.json`, `nx.json`, `turbo.json`, `WORKSPACE` or `WORKSPACE.bazel`, or a top-level `packages/` or `apps/` directory containing multiple package manifests. Any positive match enables the per-package ownership check.

The CODEOWNERS pass walks the repository for `CODEOWNERS` files at the root, in `.github/`, in `.gitlab/`, and in any nested location the platform recognizes (GitHub supports nested `CODEOWNERS` in subdirectories from 2023 onward; GitLab supports it for the `Owner` and equivalent tiers). A monorepo with only a root-level `CODEOWNERS` and no per-package coverage emits a MEDIUM finding. A monorepo with no `CODEOWNERS` at all emits a MEDIUM finding by reference to the polyglot missing-CODEOWNERS entry.

The granularity pass parses any existing `CODEOWNERS` content and checks whether each package's path is covered by a non-default rule. A package whose only coverage is the root `* @owner` line is flagged with the note "covered by default rule only, not by package-specific routing." The flag is informational on its own but compounds with any bus-factor finding to escalate the key-person risk overall.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the integration cost. After acquisition, the buyer's engineering organization typically wants to distribute monorepo packages across multiple teams. The auth package goes to the platform team, the billing package goes to the payments team, the admin tooling goes to internal tools. Without per-package CODEOWNERS, the buyer has to reconstruct the ownership map from interviews, commit history analysis, and the founder's memory before the distribution can begin. The work is doable but slow, and it tends to extend the integration timeline by weeks.

Second, the bus-factor signal disguised. A root-only `CODEOWNERS` in a monorepo is often used to satisfy a checklist requirement ("does the repo have CODEOWNERS? yes") without delivering the underlying value (does any individual package have a documented owner? no). The audit's flag is precisely that the artifact exists but does not function as intended. Buyers' diligence teams will read the root-only configuration as a key-person concentration signal, often correctly: the default reviewer is usually the founder, and the founder is usually the single point of failure the diligence is trying to surface.

Third, the operational handoff cost. Monorepos compound the cost of any ownership-handoff exercise because the work is multiplied by the number of packages. A 27-package monorepo with no per-package ownership requires 27 conversations to map ownership before any handoff, each of which is a window for the founder to be unavailable, distracted, or in transit between the audit and the close. Realistic dollar impact: 5% to 10% off the headline price when combined with a 100% single-author finding on the monorepo as a whole, because the buyer's integration cost estimate increases by the multiplier the monorepo structure introduces.

## Recommended remediation

In order, all of these need to happen:

1. **Inventory the packages.** A quick `ls packages/ apps/ libs/` or a glance at the workspace configuration produces the list. Group by functional area (auth, billing, admin, ingestion, shared utilities) so the ownership conversation is bounded.
2. **Identify the owner for each package.** For a solo founder this is "everyone is me, but I want to start handing off." For a small team this is the actual ownership map that lives in conversation. Honesty beats aspiration: a per-package ownership entry that says "Marie owns billing" when she actually does not is worse than no entry.
3. **Decide between nested CODEOWNERS and a single annotated root CODEOWNERS.** GitHub supports both. Nested files are cleaner for teams that organize work by package; a single annotated root file is faster to write and easier to scan. Pick one and apply consistently.
4. **Write the per-package ownership.** Use the standard syntax: glob pattern matching the package path, one space, the owner's GitHub or GitLab handles. List multiple owners separated by spaces when more than one person can review. Each package path should be covered by a non-default rule.
5. **Enable required-review enforcement on the platform.** In branch protection, require approving review from at least one code owner for any merge. This converts the documentation artifact into a runtime check and forces ownership to stay current as the team changes.

## How the seller could have prevented this

The structural prevention is a monorepo scaffold that includes a per-package CODEOWNERS entry as part of the package-creation tooling. Every new package created via `pnpm create`, `nx g`, `turbo gen`, or equivalent comes with an ownership entry pre-populated and a CI check that fails if the entry is missing. The team that uses the tooling consistently produces a fully-mapped CODEOWNERS as a side effect of normal development.

The behavioral prevention, for teams that have an existing monorepo with no per-package ownership, is a single working-session: list every package, write the ownership, commit the file. Most teams finish in under an hour for monorepos of up to 30 packages.

The seller who has done neither faces no immediate consequence: nothing in the codebase breaks, no CI signal fires, no user complains. The cost surfaces at exit, when the buyer's diligence team reads the root-only CODEOWNERS as a key-person concentration signal and prices the integration risk accordingly. The seller who spends an hour writing per-package ownership arrives at exit with a granular CODEOWNERS finding, a documented ownership map in the data room, and one fewer key-person concern in the diligence report.
