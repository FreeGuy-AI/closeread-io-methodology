---
finding_category: credentials
severity_observed: low
remediation_effort: XS
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; mealie packet hit this hardest)
---

# HTML test fixtures producing credential-pattern noise

## What the audit found

One audit in the batch (a self-hosted recipe-management product) produced an 872 KB packet markdown file. Investigation: the credentials scanner had flagged every recipe-HTML test fixture under `tests/fixtures/` as a "High-Entropy Secret Variable" because the recipe data contained attribute values like `data-recipe-id="aB3cD4eF5gH..."` that hit the generic-entropy regex.

Each flagged fixture had its full HTML body quoted into the packet's finding-detail section. The flagged values were 100% false positives (recipe-data attributes, not credentials), but the scanner did not know that.

This is the structural failure mode of any regex-or-entropy-based credential scanner: HTML markup contains a lot of opaque-looking strings that match credential patterns. Test fixtures are the worst case because they are deliberately structured to look like production data, and they contain large blocks of attribute values that maximize the false-positive surface area.

## How the audit caught it

Initially the scanner did not skip HTML files. The credentials specialist walked every text file with a content-type that suggested it could contain code (which included HTML for the original design rationale: a real `.env`-style cred could live in an HTML template if someone embedded one). When the file was a 50-line Python config, this was correct. When the file was a 50-KB minified HTML recipe page, this produced one finding per attribute that matched the entropy threshold.

The Day 8 fix added `.html` and `.htm` to the `SKIP_EXTENSIONS` set in the credentials specialist (Bug 4 in the Day 7 issue log) plus a `MAX_QUOTED_LINE_CHARS = 500` cap at every `RawHit` construction site. HTML files are no longer scanned for entropy patterns by default; if a real credential lives in an HTML template, the gitleaks fallback (which runs in addition to the regex-based scanner) still catches it from the raw git tree.

## Why it matters to a buyer

A packet that ships 872 KB of recipe-HTML noise is unreadable and degrades trust. The buyer's actual real findings (the 6 legitimate credential issues the packet should have surfaced) are buried under noise. The lesson is structural: the credential scanner needs to default to "scan known-source files, skip ambiguous-content files," not the reverse.

For the seller, this matters indirectly: if their codebase is going through a buyer-side scan that does not have the post-Day-8 fix, they may receive an inflated finding count from buyer's counsel and have to spend a calendar-week proving each one is a false positive. The fix is upstream of the seller.

## Recommended remediation

For the auditor running this methodology:

1. **Always skip `.html` / `.htm` by default** in the credentials scanner. The default-pass on these formats catches 99% of the real noise without missing genuine HTML-template credentials (gitleaks catches the long tail).
2. **Always cap `quoted_code` at 500 characters** at the source where the finding is constructed. This prevents a single false positive from embedding entire pages of surrounding content into the packet.
3. **Audit fixture directories deliberately** by running the credentials scanner with HTML-allowed inside `tests/fixtures/` / `__tests__/` and reviewing every finding manually before shipping. This is the "narrow exception" case where you actually want the HTML scan.

For the seller (the only thing they can do):

1. **Add a `.creds-scanner.allowlist` or equivalent file** at the repo root listing intentional false-positive paths (recipe HTML fixtures, sample-data dumps, etc.). Most credential scanners (gitleaks, detect-secrets, trufflehog) honor this file. The auditor can ship the packet referencing the allowlist as a known-safe carve-out.
2. **Move test fixtures with HTML bodies to a separate `.gitattributes`-tagged path** that scanners can configure to skip even if they do not honor the allowlist file.

## How the seller could have prevented this

Mostly they could not, since this was the auditor's tooling default. But going forward, having a single `.gitattributes` entry like `*.html generated linguist-generated=true` for fixture directories signals to many tools (including GitHub's language detection) that these files are not real source and can be skipped.

## When skipping HTML might be the WRONG default

In a repo where HTML templates contain server-side rendering directives that legitimately embed credentials (e.g. a Rails view that hard-codes an API key inline for debugging), the default skip will miss it. The gitleaks fallback usually catches these because it scans the raw git tree, but if the gitleaks coverage is incomplete the finding will be missed.

The doctrine: prefer false-negatives over false-positives in the credentials scanner specifically, because the noise cost of false-positives on HTML is enormous (a 872 KB packet that obscures real findings) while a single missed credential in an HTML template is recoverable (a separate gitleaks pass against the raw tree picks it up).
