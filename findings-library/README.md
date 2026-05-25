# Findings library

Anonymized real findings from delivered audits. Each entry is a small case study a contributor or reader can learn the pattern from.

These entries are anonymized: company names, domains, and specific identifying details come out. Revenue ranges, codebase sizes, and stack details stay in. The point of an entry is the pattern, not the specific subject.

## How to read an entry

Each entry sits in `findings-library/{stack}/{short-slug}.md` and walks the reader through:

* What the audit found
* How the audit caught it (deterministic tool, hybrid, LLM-assisted)
* Why it mattered to the buyer
* What the recommended remediation was
* How the seller or buyer responded

## How to contribute an entry

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the entry frontmatter and structure. The bar is: the pattern is durable (will recur in future audits), the entry is sufficiently anonymized (no identifying details), and the remediation guidance is concrete (a reader can act on it without guessing).

## Current entries

The library ships empty at launch. The first 5 entries land within 30 days of launch as we deliver the first cohort of paid Founding Alpha audits. After that, the library grows on the pace of customer engagements plus outside contributions.

If you have run an audit yourself and have a pattern worth banking, your contribution is the fastest way to fill this library out. Open an issue or send a PR.
