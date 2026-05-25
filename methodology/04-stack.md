# 04 Stack and hireability

The single largest post-close surprise in indie SaaS M&A is not security debt. It is the buyer discovering they cannot hire engineers for the stack they just bought. This finding is invisible to financial diligence, invisible to most code-quality tooling, and almost always understated by the seller. Closeread's stack artifact surfaces it before the LOI.

The buyer's question is operational: "if the seller's lead engineer leaves day 30, what is my time-to-hire and what is the salary delta from a mainstream stack?" Closeread answers this with a deterministic rubric, not a model judgment.

## What this artifact covers

Two signals from the codebase plus one rubric:

1. **Primary language identification.** What is the dominant source language by line count, filtered to actual source code (not lockfiles, not JSON locale dumps, not Markdown docs)? This is harder than it looks; many codebases get mis-identified by line-count-naive tools.
2. **Framework detection.** What canonical framework is the codebase built on (Django, Rails, Next.js, Phoenix, Spring Boot, etc.)? Detection is signature-based against the manifest dependencies.
3. **Hireability tier mapping.** Each language and framework lives in one of four tiers per a curated, version-locked rubric: easy / moderate / niche / rare. The tier feeds the finding severity.

## The hireability rubric (current as of 2026 US labor market signal)

The tier table is conservative and version-locked here so audit output is deterministic. The 2026 baseline:

- **Easy** (high supply, low replacement cost): JavaScript, TypeScript, Python, Java, C#
- **Moderate** (adequate supply, mid replacement cost): PHP, Ruby, Go, C++, Rust, Kotlin, Swift
- **Niche** (thin supply, high replacement cost): Scala, Elixir, Clojure
- **Rare** (tiny supply, very high replacement cost; deal-killer signal): Erlang, Haskell, F#, OCaml, Crystal, Nim

Frameworks adjust the language baseline up or down. Canonical frameworks in the easy or moderate language don't change the tier. Niche framework choices on mainstream languages (Phoenix on Elixir, Akka on Scala) keep the niche label. Rare framework choices in any language (Yesod on Haskell) escalate to rare.

The rubric updates annually or when a major shift hits the labor market. Elixir is the closest one to a tier-change candidate in 2026 (Phoenix LiveView has materially increased engineer supply); we may move it to moderate in the 2027 update.

## Primary language: what NOT to do

A common mistake in code-survey tools is to compute primary language as `max(language)` from the raw line-count breakdown. This is structurally wrong for the buyer-DD use case because:

- A TypeScript SaaS with i18n locale files in JSON (often 100k+ lines) ends up reporting JSON as primary.
- A Python web app with auto-generated Markdown docs reports Markdown as primary.
- A Vue project with vendored fixture dumps reports YAML or JSON as primary.

The fix is to filter non-source formats out of the primary-language calculation BEFORE picking the max. Closeread's `NON_SOURCE_LANGUAGES` filter excludes: JSON, YAML, TOML, Markdown, HTML, CSS, SCSS, SQL. This was Bug 5 in the Day 7 audit batch; the post-fix primary-language signal is the canonical one the artifact uses.

## How the audit runs the stack scan

Deterministic. Three steps:

1. **Compute the source-only language breakdown** from the ingest pass. Apply `NON_SOURCE_LANGUAGES` filter. Pick the max as primary; report secondary and tertiary if they exceed 10% of source LOC.
2. **Walk all manifest dependencies** for canonical framework signatures (curated list of ~20 frameworks in v1; expanding).
3. **Map primary language tier + detected framework tier** to a finding severity per the rubric.

If the primary language is in the niche tier, emit a MEDIUM finding. Rare = HIGH. Easy + moderate = no finding (clean stack from a hireability perspective). Frameworks add findings only when they ESCALATE the tier (a niche framework on an easy language emits a MEDIUM); they do not de-escalate.

## What "good" looks like in the packet output

A clean stack artifact has:

- Primary language in the easy or moderate tier with a percentage of source LOC above 60%.
- No niche or rare frameworks detected, OR the niche framework is documented in the data room with hireability mitigation (current team's actual size, consultancy relationships, contractor pools).
- A statement of secondary and tertiary languages if the polyglot ratio is meaningful.

A seller with a niche-stack codebase who hands a buyer a packet that names the stack proactively, includes a written hireability mitigation, and references the seller's own engineering retention as part of the deal structure has materially de-risked the conversation. The hireability finding does not kill the deal; concealing it does.

## Detection caveats

- **Polyglot repos.** Many modern SaaS have substantial frontend (TypeScript) + backend (Python or Go) splits. The artifact reports primary, secondary, tertiary explicitly when each exceeds 10% of source LOC. The hireability tier for the worst (highest-tier-number) is the artifact's headline.
- **Generated code.** Protobuf stubs, OpenAPI clients, ORM models are excluded from the LOC denominator (same exclusion as the reliability artifact).
- **Framework detection misses.** v1 covers ~20 canonical frameworks; less common ones (Hanami in Ruby, Quart in Python) may not match. The artifact emits an INFO note "framework not in canonical signature set" when this happens; the language tier still drives the headline finding.
- **Library detection vs framework detection.** Importing `react` is detection of React (a framework). Importing `lodash` is not (a library). The signature list is curated to frameworks only.

## Recommended remediation for sellers with a niche or rare stack

You cannot re-write your stack in 60 days. The remediation is disclosure + mitigation, not change:

1. **Name the stack proactively** in the packet narrative. "This product is built on Phoenix (Elixir). Hireability tier: niche. Here is our 3-paragraph mitigation."
2. **Quantify your current team's stake.** Tenure, equity, retention provisions. If the founder is the only engineer and plans to exit at close, the buyer needs to know that.
3. **Provide contractor / consultancy relationships** familiar with the stack. Names, rates, capacity. The buyer's worst case is "we cannot find help"; pre-existing relationships solve that worst case.
4. **Surface hidden upside.** Some niche stacks have hidden labor-market advantages (Elixir engineers are paid less competitively than Python despite being scarce; Phoenix LiveView is reducing the team-size need for full-stack work). If true for your case, name it.

The buyer-side research is unambiguous (Gilmore at Xenon Partners, samanamp's post-close post-mortem on HN, multiple other practitioner accounts): the seller who proactively named their stack hireability and provided a mitigation experienced a 20-40% smaller deal-discount than the seller who let the buyer discover it. The disclosure is the move.

## Related artifacts

- `10-key-person.md` (TODO): hireability and bus-factor are joint signals. A niche stack with a single-author concentration is a deal-killer combo. The packet cross-references when both surface.
- `09-test-coverage.md` (TODO): a niche stack with low test coverage is harder to onboard a replacement onto.
- The findings-library cross-cutting entry on stack-hireability lives at `../findings-library/polyglot/` (placeholder; specific entry being drafted).
