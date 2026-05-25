# 10 Key person: who has authored this code, and what is the bus factor

The single largest source of post-close surprise after stack hireability (artifact 04) is the buyer discovering the seller's lead engineer is structurally irreplaceable. Buyers walk in disbelieving the seller's "the team can run it" claim until they see git blame distribution. The key-person artifact runs git blame for them, before the LOI.

The buyer's question is unromantic: "if the seller's lead engineer leaves day 30, what fraction of the production system is in their head and nowhere else?" The git history is the only source of truth that does not lie, and it is also the source of truth the seller has the least control over once the audit runs.

## What this artifact covers

Three signals from the git history:

1. **Commit-share distribution.** Top author share, top two authors combined, total contributor count over the trailing 365 days (configurable window). This is the bus-factor signal.
2. **Dormant contributors.** Authors with 5+ historical commits whose last commit is more than 90 days old. These contributors may still hold IP / domain knowledge; the buyer's M&A counsel will ask about their contributor agreement status.
3. **Bot contributors.** A CI bot (`github-actions[bot]`, `dependabot[bot]`) showing up as a top author indicates the seller is committing via automation. This usually means a founder authoring through automation; the human attribution behind the bot is invisible to git log alone.

## What this artifact does NOT cover

- The buyer's separate runtime-knowledge audit. The key-person artifact reads git; the buyer's engineering team will also want to interview the seller's engineers and walk through production decisions verbally. The artifact is the structural signal, not the qualitative one.
- Contributor agreement / IP assignment status. The packet's IP-ownership artifact (05) covers this; key-person merely flags which historical contributors should be reviewed there.
- Cross-employee project knowledge. If two engineers at the seller's company know the same module, git blame still shows commit share. The artifact under-reports redundancy in this case; the seller should disclose proactively in the packet narrative.

## How the audit runs the key-person scan

Deterministic, no LLM. Run `git log --since=<window> --format='%an|%ae|%aI'` against the repository, aggregate by email (canonical author identity), compute:

- Total commits in window
- Per-author commit count
- Per-author first commit + last commit timestamps
- Per-author share (commits divided by total)

Sort by commit count desc. Take top 5 for the distribution narrative. Emit findings per the severity rubric below.

The scanner also checks the shallow-clone state BEFORE running the distribution analysis (per Bug 7 doctrine; see below). On a shallow clone the scanner emits a single INFO finding ("Shallow clone, bus factor inconclusive") and skips the rest of the analysis.

## Severity rubric

- **HIGH**: top author owns more than 70% of commits in the trailing 365-day window. This is the single-point-of-failure signal.
- **MEDIUM**: top author owns 50-70% AND top 2 combined own more than 80% (two-person concentration).
- **LOW**: dormant contributor cluster (5+ historical commits, no commits in 90 days). One LOW finding per cluster, not per dormant individual.
- **INFO**: shallow-clone-cannot-measure case; analysis skipped explicitly.

The artifact health score is a deterministic function of the finding mix. HIGH = 40; MEDIUM = 70; LOW = 85; INFO (only the shallow-clone case) = 100 (signal missing, not bad).

## The shallow-clone doctrine (Bug 7 fix)

Most audits run against shallow clones (`git clone --depth 1`) for disk + time efficiency. On a shallow clone, only the most-recent N commits are visible. Every shallow-cloned repo will present as "1 commit, 1 author at 100%" or close to it, which is structurally misleading.

Pre-Day-8 the scanner emitted a HIGH single-contributor finding on every shallow clone. This was wrong. Post-Day-8 the scanner detects shallow state via `.git/shallow` existence OR `git rev-parse --is-shallow-repository`, and on a shallow clone emits a single INFO finding "Shallow clone, bus factor inconclusive (re-run on a full-history clone for a real result)." Health stays at 100. No false-positive HIGH.

The doctrine: when the data does not support the finding, the artifact says so explicitly and asks for better data. It does not emit a structurally-wrong finding to look thorough. This is named in the related findings-library entry [`shallow-clone-bus-factor-inconclusive.md`](../findings-library/polyglot/shallow-clone-bus-factor-inconclusive.md).

## What "good" looks like in the packet output

A clean key-person artifact has:

- Top contributor share under 50% in a deep-history clone.
- At least 3 active contributors (each with commits in the last 30 days).
- No dormant cluster of size more than 1 (single dormant contributor is fine; multiple is a contributor-agreement question).
- Cross-referenced narrative in the packet's IP-ownership artifact (05) confirming any dormant contributor signed a CLA or assignment.

A seller with a single-author codebase who hands a buyer a packet that names this proactively, includes documentation (ADRs, runbooks, walkthroughs), and provides a written knowledge-transfer plan has materially de-risked the conversation. The bus-factor finding does not kill the deal; concealing it does.

## The bot-as-top-author case

Some repos show `github-actions[bot]` or `dependabot[bot]` as a top contributor by commit count. This usually means a founder authoring through automation (the bot creates the merge commits, the human authored the code).

The artifact emits a separate INFO finding when a bot is in the top 3 by commit count, recommending the seller either:

1. Reconfigure the bot to use the real author's identity (preserves the git blame signal post-close), OR
2. Document the human attribution explicitly in the data room (most buyer-side counsel accepts this as a reasonable workaround).

## Recommended remediation order

For a seller preparing to list with a HIGH bus-factor finding:

1. **Write architectural decision records (ADRs) for the last 10 significant decisions.** Two days of focused writing. Each ADR follows the standard template: context / decision / consequences / alternatives. The single highest-ROI pre-close documentation effort.
2. **Bring a second engineer on the team for at least 60 days before close**, even on contract. Real work on the codebase, pair-reviewing PRs. Re-run the audit at end of contract; the share moves from 100/0 to 70/30, downgrading the finding from HIGH to MEDIUM.
3. **Write a knowledge-transfer plan** in the data room naming which modules the founder owns, what the bus-factor risk is on each, and what the buyer needs to do in the first 90 days to absorb that knowledge.

The buyer-side research is consistent (multiple practitioner post-mortems, Gilmore at Xenon, samanamp on HN): a seller who proactively named bus-factor risk + provided documentation + named retention provisions experienced 30-50% smaller deal-discounts than a seller who let the buyer discover it. The disclosure is the move; the documentation is the leverage.

## Detection caveats

- **Shallow clones report INFO, not HIGH.** Per the doctrine above. Most batch audits run shallow for efficiency.
- **Email aliases.** If a contributor has multiple email addresses (work + personal), the artifact under-counts unless emails are normalized. Sellers can fix this pre-listing by mailmap-ing.
- **Commit window.** Default is 365 days; configurable. Longer windows surface the contributor history; shorter windows surface current activity. The packet narrative should name the window used.
- **Force-pushed branches.** A `git filter-repo` history rewrite (e.g. for credential scrubbing per artifact 07) changes the commit hashes but preserves the author metadata. The bus-factor signal survives history rewrites cleanly.

## Related artifacts

- `04-stack.md`: bus-factor and stack-hireability are joint signals. A niche stack with single-author concentration is a deal-killer combo.
- `05-ip-ownership.md` (TODO): dormant contributors raise the contributor-agreement question that IP ownership covers.
- The findings-library entries [`single-author-100-percent-commit-share.md`](../findings-library/polyglot/single-author-100-percent-commit-share.md) and [`shallow-clone-bus-factor-inconclusive.md`](../findings-library/polyglot/shallow-clone-bus-factor-inconclusive.md) cover the two cross-cutting patterns observed across the Closeread sample audits.
