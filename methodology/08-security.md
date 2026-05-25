# 08 Security: what does standard static analysis surface, and what is the pre-pentest signal

The buyer's question on security is conservative: "is this codebase going to pass a standard SOC2 / ISO 27001 / pentest engagement, or am I inheriting weeks of remediation?" The security artifact runs the standard static analysis layer that a pentest would start from, so the seller and the buyer see the same baseline.

This artifact is NOT a substitute for a pentest. It is the cheaper, earlier, repeatable signal that catches the bottom 80% of findings a pentest would also catch.

## What this artifact covers

Three detection layers:

1. **Static analysis security testing (SAST).** Wrap canonical SAST tools per language: Bandit for Python, Semgrep for polyglot, gosec for Go, brakeman for Ruby, ESLint security plugins for JS/TS. Each tool's findings are normalized into Closeread's Finding schema.
2. **Disclosure policy.** Presence and content quality of `SECURITY.md` at repo root. Absence is a finding because it signals weak security culture even when no active vulnerability exists.
3. **Pre-pentest signal.** A summary score combining SAST density + disclosure presence + dependency-CVE backlog (cross-referenced from artifact 03). This is the proxy for "if a pentest fires next week, how many findings does the seller already know about."

## What this artifact does NOT cover

- Runtime / dynamic security testing. Closeread does not execute the codebase.
- Authentication / authorization logic review. That requires manual security engineering.
- Cryptographic implementation review. Use of `random` instead of `secrets`, custom AES implementations, etc., are flagged by SAST when patterns match; full crypto review is a separate engagement.

## How the audit runs the security scan

Deterministic, wraps existing tools. Per language detected in the ingest:

1. Run the language's canonical SAST tool with default rules. Parse JSON / SARIF output.
2. Map each finding's severity to Closeread's Severity enum (CRITICAL / HIGH / MEDIUM / LOW / INFO).
3. Apply path-based downgrades (findings in `tests/` / `fixtures/` drop one severity level).
4. Check for `SECURITY.md` at repo root. Absence emits a MEDIUM finding (per the cross-cutting pattern observed in 8 of 22 sample audits).
5. Cross-reference SCA findings count + severity from artifact 03; if the SCA backlog is large, security artifact emits a HIGH "pre-pentest signal" summary finding.

## Severity rubric

- **CRITICAL**: SAST tool emits a CRITICAL (Bandit's B105/B324 class, Semgrep's "exploit" tagged rules).
- **HIGH**: SAST tool emits a HIGH OR the cross-referenced SCA backlog exceeds the pre-pentest threshold OR `SECURITY.md` absent on a public-facing repo.
- **MEDIUM**: SAST MEDIUM, or `SECURITY.md` absent on a private repo.
- **LOW**: SAST LOW, or path-downgraded findings from test files.

## What "good" looks like in the packet output

A clean security artifact has zero CRITICAL/HIGH SAST findings, `SECURITY.md` present at repo root with a documented disclosure path, and a documented pentest history (even if "no pentest yet"; the document of decision is the signal).

A seller who can hand a buyer a clean security artifact has materially shortened the buyer's pre-close security DD. The pentest still happens (in most deals); the artifact reduces what the pentest needs to surface.

## Recommended remediation order

1. **Add `SECURITY.md`** (30 min; see findings-library [missing-security-md-no-disclosure-policy.md](../findings-library/polyglot/missing-security-md-no-disclosure-policy.md)).
2. **Fix all CRITICAL SAST findings** before listing.
3. **Fix HIGH SAST findings** in priority order; document trade-offs in the data room.
4. **Set up SAST in CI** so the cadence is enforced.
5. **Optionally commission a pentest** pre-listing. Some buyer-side teams treat a clean pentest report as a multiplier on offer price.

## Detection caveats

- **Per-language SAST coverage varies.** Bandit is strong for Python; Semgrep covers everything but needs a curated ruleset. The artifact narrative names which tool ran per language.
- **False positives are common in SAST.** Sellers should expect to spend a calendar-day reviewing SAST output before remediation. The packet narrative should call out which findings were reviewed and accepted as not-actionable.
- **Tool availability.** If a SAST tool is not installed, the artifact emits an INFO note "tool X not present, language Y not scanned." Sellers running the audit should install the canonical tools first.

## Related artifacts

- `03-sca.md`: dependency CVEs feed this artifact's pre-pentest summary signal.
- `07-credentials.md`: hardcoded credentials are a security finding; the credentials artifact is the deeper scan.
- The findings-library entry [missing-security-md-no-disclosure-policy.md](../findings-library/polyglot/missing-security-md-no-disclosure-policy.md) covers the cross-cutting pattern.
