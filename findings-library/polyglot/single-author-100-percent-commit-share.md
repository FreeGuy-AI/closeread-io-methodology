---
finding_category: key_person
severity_observed: high
remediation_effort: L
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# Single human author with 100% of commits over the last 365 days

## What the audit found

Three audits in the same batch. Three different stacks (TypeScript indie SaaS, PHP infrastructure tool, TypeScript document-signing platform). One identical finding: the top contributor over the trailing 365 days held 100% of the commit share, with the next contributor at 0%.

In two of the three cases, the single author was the founder. In the third, the only "author" of record was a CI bot (`github-actions[bot]`), which usually means a founder authoring through automation and not leaving a trail under their own name.

## How the audit caught it

Deterministic. The key-person specialist runs:

```
git log --since='365 days ago' --format='%aN' | sort | uniq -c | sort -rn
```

then computes a Top-5 distribution. A HIGH finding fires whenever a single non-bot author holds more than 80% of commits in the last 365 days against a codebase larger than 50k LOC.

The bot-author case (`github-actions[bot]` at 100%) gets a special note: the audit cannot detect the human behind the bot from `git log` alone, and the seller needs to either reconfigure the bot to use the real author's identity or document the human attribution in the data room.

## Why it matters to a buyer

Buyer-side research (publicly cited from acquisition consultancies and post-mortem studies) identifies key-person risk as the **second-largest source of post-close surprise**, behind only stack hireability. The acquisition price embeds an assumption that engineering knowledge survives the transaction. In a 100% single-author codebase, it does not, unless the author signs a multi-year earn-out with retention provisions that often exceed 30% of the headline deal value.

The compounding problem: a single author over 365 days means a single author for **all production decisions** in that window. Every architectural choice, every dependency selection, every implicit constraint, every "we tried X and it didn't work" is in one person's head and nowhere else.

When that person leaves (and post-acquisition founder departures within 18 months are the rule, not the exception), the buyer loses the only living source of truth for why the system is the way it is.

## Recommended remediation

Pre-close, in order of impact:

1. **Architectural decision records (ADRs) for the last 10 significant decisions.** Two days of focused writing. Each ADR follows the standard template: context, decision, consequences, alternatives considered. This is the single highest-ROI pre-close documentation effort.
2. **A second engineer on the team for at least 60 days before close,** even on a contract basis, doing real work on the codebase and pair-reviewing PRs. The audit re-runs at end of the contract; the commit share moves from 100/0 to 70/30, which downgrades the finding from HIGH to MEDIUM.
3. **A written knowledge-transfer plan** in the data room that names which modules the founder owns, what the bus-factor risk on each is, and what the buyer needs to do in the first 90 days to absorb that knowledge.

## How the seller could have prevented this

The structural prevention is "hire someone, even part-time, even a contractor, before Year 2." This is rarely commercially viable for a bootstrapped solo founder.

The realistic prevention is documentation discipline: ADRs for every significant decision, READMEs in every package, comments on every non-obvious code path. The seller who has done this arrives at exit with a key-person health score in the 60-80 range despite still being a solo author, because the **knowledge** has been externalized even if the **execution** has not.

The seller who has not is in a much harder position. There is no fast remediation for a year of undocumented decisions, only a slow one.
