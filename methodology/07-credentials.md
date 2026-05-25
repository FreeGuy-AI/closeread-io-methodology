# 07 Credentials: what secrets exist in the codebase, and what is the rotation posture

The credentials artifact answers the buyer's most viscerally-felt question: "if I run gitleaks on this repo right now, will I find a live AWS key or a live Stripe secret?" The seller has the most defensible answer when they can hand the buyer a packet that says "we ran the scan, here is what we found, here is what we rotated, here is the policy preventing recurrence." The least-defensible answer is silence followed by the buyer running their own scan and finding something.

## What this artifact covers

Three detection layers in increasing-cost order:

1. **Path-based detection.** Any file named `.env`, `.env.*`, `credentials.json`, `id_rsa`, `*.pem` at any path in the repository. The presence alone is a HIGH finding regardless of content.
2. **Pattern-based detection.** Regex matches for canonical credential shapes: AWS Access Key (`AKIA[A-Z2-7]{16}`), Stripe secret (`sk_live_...`), GitHub PAT (`gh[pousr]_...`), Anthropic API key (`sk-ant-...`), OpenAI API key (`sk-...`), Slack token (`xox[baprs]-...`), SSH private key PEM, generic Bearer token, high-entropy variable in a name suggestive of a secret (key / secret / token / pass / pwd / password).
3. **Optional gitleaks fallback.** If `gitleaks` is on the system PATH, run it against the repo for richer signature coverage + git-history exposure. Findings supplement the pattern-based ones (no duplication).

Cross-cutting deduplication: a single file flagged by multiple patterns gets collapsed to one finding per category to avoid noise.

## What this artifact does NOT cover

- **Production-runtime credentials.** Anything injected at runtime via environment variables, secrets managers, or CI/CD pipelines is outside the repository surface. The buyer's separate runtime DD covers this.
- **Browser-side or client-side credential exposure.** If your frontend bundles an API key in webpack output, the artifact may catch it depending on whether the bundled output is in the repo, but the canonical detection is browser-DevTools or a tool like Snyk Code which we do not vendor here.
- **Historical credentials in deleted-then-restored files.** The pattern + path scan looks at the current tree; gitleaks (if installed) looks at the full history. If gitleaks is not installed and the seller deleted a `.env` in commit N+1 after committing it in commit N, the current scan will miss it but git-history-scrubbing tools will find it.

## How the audit runs the credentials scan

Deterministic. For each file in the repository:

1. **Skip non-source extensions** by default. The skip list is `{".md", ".txt", ".csv", ".json", ".html", ".htm"}`. Exception: any file named `.env` or `.env.*` is always scanned regardless of extension.
2. **Skip files larger than 500 KB** (minified bundles, generated assets).
3. **Run each regex pattern** against the file's contents. Each match becomes a `RawHit`.
4. **Cap `quoted_code` at 500 characters** per match. This prevents a single finding from embedding pages of surrounding context (Bug 4 in the Day 7 audit batch surfaced this; the post-fix cap is the production default).
5. **Collapse repeated hits in the same file** into a single summary hit when there are more than 10 of the same pattern in the same file (the "fixture file" pattern). The collapsed finding gets reduced severity + a "likely a fixture" rationale.
6. **Annotate test paths.** Files under `tests/`, `__tests__/`, `fixtures/`, `mocks/`, `spec/`, etc. get their findings downgraded (CRITICAL becomes LOW for AWS/Stripe live keys; the SSH-private-key pattern stays HIGH because a real SSH key in a test fixture is still real).
7. **Run gitleaks if installed** for supplemental findings, timeout 60s.

## Severity rubric

Live credentials are CRITICAL by default outside test paths:

- **CRITICAL**: AWS access key, Stripe live secret, GitHub PAT, Anthropic API key, OpenAI API key, Slack bot token in production code paths.
- **HIGH**: Stripe test key, generic Bearer token (lower confidence), SSH/PEM private key (anywhere), committed `.env` file (anywhere; the file itself is the finding regardless of contents).
- **MEDIUM**: high-entropy variable in a sensitive name (key/secret/token/pass/pwd) outside a test path.
- **LOW**: same patterns in test paths, OR the collapsed "many hits in one file" summary finding.

The artifact health score is computed from the finding-severity mix. A single CRITICAL drops it to ~20. A clean repo scores 100.

## What "good" looks like in the packet output

A clean credentials artifact has:

- Zero CRITICAL findings (no live credentials anywhere).
- Zero `.env` family files committed at any path. `.env.example` is OK if the values are obvious placeholders (`KEY=YOUR_KEY_HERE` style).
- A statement in the packet narrative that gitleaks was run AND that the git history was scrubbed if any past commits ever contained credentials.
- A `SECURITY.md` documenting the rotation policy + secrets-manager-of-record (Vault, AWS Secrets Manager, 1Password, Doppler).

A seller who can hand a buyer a clean credentials artifact + a screenshot of the current secrets-manager-of-record dashboard has materially removed the largest single deal-killer in indie SaaS DD. The credentials finding alone has killed more deals than any other class of finding in 2024-2026 per the public M&A post-mortems we have read.

## The Documenso-class case (anonymized doctrine)

One audit in the Day 7 batch surfaced a CRITICAL committed secret in the seller's git history (anonymized in the findings-library; the affected commit was years old, the credential was long-rotated, but the history contained the original committed value).

This is the worst-case credential finding. It is also the most common one a buyer's M&A counsel will find, because they will run gitleaks against the full history regardless of what the seller does at the current tree. The remediation is git history rewriting (`git filter-repo` or BFG) + force-push + collaborator re-clone, which is a calendar-week of work + a credential-rotation event for every credential the historical exposure touched.

The doctrine: the seller who proactively rewrites history and rotates pre-listing is in a materially better position than the seller who lets the buyer find it. The packet from a seller who has done this should explicitly say so. The buyer's counsel reads this as a sophistication signal.

## Recommended remediation order

For a seller preparing to list with a non-trivial credentials backlog:

1. **`git rm --cached`** any committed `.env` family files and add to `.gitignore`. Commit immediately.
2. **Rotate every credential** that was ever in any of those files. Assume compromise from the first commit they appeared in.
3. **Run `gitleaks detect --no-git` against the current tree** to verify nothing else is hiding.
4. **Run `gitleaks detect` against the full git history** (no `--no-git` flag) to surface anything in past commits.
5. **Decide on history scrubbing.** For an indie SaaS exit, the answer is usually "yes, scrub" because the calendar cost is days and the post-close optics are worth it. For a heavily-forked open-source project, the answer is "no, document instead" because the scrub breaks forks.
6. **Add a pre-commit hook** (gitleaks, detect-secrets, or trufflehog) so the pattern cannot recur.
7. **Add `SECURITY.md`** documenting the disclosure path + the secrets manager + the rotation cadence.

## Detection caveats specific to ecosystems

- **HTML / Markdown** are skipped by default per Bug 4 doctrine. If a real credential lives in an HTML template (rare), the gitleaks fallback will catch it from the raw git tree.
- **Frontend bundles.** A minified webpack output > 500 KB is skipped; the unminified source is the canonical detection target. If your build process strips secrets at compile-time but the unminified source has them, that is still a finding.
- **Encrypted secrets.** A `.env` encrypted with `sops` or `ansible-vault` will be skipped by content pattern (high entropy is expected) but flagged by path (`.env` family). The packet narrative should clarify which.
- **Multi-line PEM keys.** The SSH private-key pattern requires the `-----BEGIN ... PRIVATE KEY-----` header line; the body is not parsed. A key without the header line will be missed (unusual; most legit PEM has the header).

## Related artifacts

- `08-security.md` (TODO): credentials are a security finding; the security artifact also runs Bandit / Semgrep / gosec for the broader static-analysis pass. The two artifacts cross-reference.
- `04-stack.md`: a polyglot codebase has more places for credentials to hide; the credentials artifact runs per-language file globs.
- The findings-library entry [committed-env-file-in-repository.md](../findings-library/polyglot/committed-env-file-in-repository.md) covers the cross-cutting pattern observed in 7 of 22 Closeread sample audits.
