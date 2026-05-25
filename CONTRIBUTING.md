# Contributing to Closeread Methodology

Thanks for considering a contribution. This document is the moat. Read it before opening a PR.

The repo's value compounds only if every merged change makes the methodology more rigorous, more honest, and more useful to a founder selling their codebase. Contributions that drift toward marketing voice, speculative patterns, or unciteable claims get bounced.

## TL;DR

1. Open an issue first for anything bigger than a typo. Discuss before you build.
2. Every substantive PR ships with a change-note file in `change-notes/`.
3. New stack appendices and findings library entries must follow the templates.
4. Experimental work goes in `experimental/` subfolders. It graduates to stable when battle-tested.
5. Maintainer review is required for methodology changes (anything in `/methodology`).
6. Voice rules: no marketing copy, no em dashes, founder-to-founder tone, every claim cites.

## Before you open a PR

**Open an issue first** if your change is bigger than a typo, a broken link, or a clarifying word. The issue is where the design discussion happens. If you skip this step and the PR conflicts with the methodology's direction, the discussion has to happen on the PR thread itself and that wastes everyone's time.

Use the issue templates in [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/):

- `methodology-change` for any change to `/methodology`
- `new-appendix-request` for a new stack appendix
- `finding-pattern` for a new findings library entry
- `bug` for factual errors, broken links, broken examples

If your contribution is a single language appendix or a single findings library entry, you can often skip the issue and go straight to a PR. For anything that changes how Closeread does an audit, file an issue first.

## What kinds of changes belong here

Yes:

- New stack appendices (Python, PHP, Ruby, Go, Java, Rust, Elixir, mobile, infrastructure-as-code).
- New entries in the findings library, citing a real audit (anonymized) where the pattern surfaced.
- Clarifications, typo fixes, broken-link fixes, dead-code removal.
- New examples in the packet template, sanitized from real audits with customer permission.
- Tooling improvements (CI, link-check, mdBook build, new GitHub Actions).
- Translations of existing docs into other languages (open an issue first).
- Reference CLI work once Day 180 scaffolding is in (track via `reference-cli` label).

No:

- Speculative findings ("here is a pattern that might cause issues") without a cited audit.
- Marketing voice or sales copy. The README's bottom section is the only place commercial pitch belongs.
- New methodology phases or core changes proposed without an issue discussion first.
- AI-generated bulk content (we accept AI-assisted work, but the human or agent submitting it has to vouch for every claim).
- Framing that drifts from the brand premise. Closeread audits are AI-end-to-end. Methodology entries must describe the heterogeneous-model adversarial reviewer accurately, not retrofit a default audit-firm framing. See `/methodology/05-adversarial-review.md`.

## Change notes (the single most-important convention)

This is the convention from CodeQL that most reduces drift in a multi-contributor methodology repo. Adopt it from day one.

**Every substantive PR adds one file to `change-notes/`.** Filename pattern: `change-notes/{PR-NUMBER}-{short-slug}.md`. Example: `change-notes/47-python-async-session-leak-pattern.md`.

The file is short. Three sections:

```markdown
## What changed
One paragraph describing the change in user-visible terms. Read like a release note.

## Why
One paragraph describing the audit or finding that triggered the change. Cite the
audit ID if it was a Closeread audit, or the public source if external.

## Migration
If maintainers or downstream consumers need to do anything when they pull this
change, describe it here. Most changes have no migration. "None" is a valid answer.
```

Trivial changes (typo fixes, broken-link repairs, dead-code removal) do not need a change-note. The maintainer reviewing the PR is the judge.

CHANGELOG.md is auto-generated from `change-notes/` at release tag cuts.

## New stack appendix workflow

The single highest-leverage contributor pull. Process:

1. Open a `new-appendix-request` issue. Name the stack and the maintainer (you, presumably).
2. Copy [`appendices-by-stack/_template/`](appendices-by-stack/_template/) to `appendices-by-stack/<your-stack>/`.
3. Fill out every section in the template. Empty sections fail review.
4. Each finding pattern in your appendix must cite at least one audit (Closeread or public).
5. Open a PR with the appendix folder and a change-note.
6. Maintainer review takes 1 to 5 business days. We will not bikeshed; we will check that the patterns are real and the citations resolve.

Once merged, you are the appendix's maintainer of record. We will route stack-specific issues to you. You can step down anytime by opening an issue; we will find someone else or freeze the appendix.

## New findings library entry workflow

The catalog grows monthly as audits ship.

1. Each entry is one file: `findings-library/F-{NNN}-{short-slug}.md`.
2. Use the [`_template`](findings-library/_template/) structure.
3. Anonymize the source audit completely. No customer name, no repo URL, no identifying details that could not appear in 100 other codebases.
4. Cite the audit ID in the change-note, not in the public entry.
5. Cross-reference by stack in `findings-library/by-stack/<stack>.md`.

## Methodology change workflow (slowest path, highest bar)

Anything in `/methodology` is the canonical Closeread audit playbook. Changing it requires:

1. An issue tagged `methodology-change` with the proposed change, the rationale, and the audits that motivated it.
2. A maintainer-led discussion period of at least 7 days.
3. A PR with a change-note that explicitly says "methodology change" in the title.
4. Two maintainer approvals.

We are slow here on purpose. Methodology drift breaks downstream audits.

## Experimental work

If you want to propose a new specialist agent role, a new buyer-impact scoring tweak, or a new finding-category taxonomy, put it under `experimental/` first. Pattern from CodeQL.

```
methodology/experimental/<your-proposal>.md
appendices-by-stack/<stack>/experimental/<your-pattern>.md
findings-library/experimental/F-XXX-<your-finding>.md
```

Experimental work graduates to stable after:

- It has been applied in at least 3 audits (Closeread or external) with the maintainer linked.
- A maintainer signs off.
- The graduation move (file rename) ships as its own PR with a change-note describing what graduated and why.

## Style and voice

Closeread's voice is founder-to-founder. Things that fail review on voice alone:

- Marketing copy. "Revolutionary," "industry-leading," "best-in-class," any sentence that could appear in a press release.
- AI-cliche openings. "In today's fast-paced world," "More than ever," "Imagine a world where."
- Em dashes anywhere. Use commas, periods, or double-hyphens (`--`) if you genuinely need an aside.
- Vague claims. "Many founders find" needs a citation; "8 of 12 audits to date surfaced this" does not.
- Hyped severity. "Critical" means deal-blocking. If it is not deal-blocking, it is not critical.

Read [thoughtbot/guides](https://github.com/thoughtbot/guides)'s "Avoid / Don't / Prefer / Use" pattern as the model.

## PR template

When you open a PR, GitHub will load [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md). Fill out every section. PRs with blank sections will be asked to fill them before review.

## Code of conduct

We follow [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). The summary: do not be a jerk. Disagreement on the methodology is welcome and encouraged; disagreement on a contributor's right to participate is not.

## Maintainer response time

We respond to every issue and PR within 48 hours on weekdays. If your PR has been silent for longer, ping the issue or DM Free Guy on the channel listed in [.github/MAINTAINERS.md](.github/MAINTAINERS.md). Maintainers go on vacation; we are not ignoring you.

## License

By contributing, you agree your contribution is licensed under MIT, the same as the rest of the repo. No CLA. Inbound = outbound, the OpenZeppelin and Anthropic Cookbook convention.
