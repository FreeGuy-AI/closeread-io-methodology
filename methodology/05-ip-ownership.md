# 05 IP ownership: who owns this code, under what license, with what contamination

The buyer's M&A counsel reads this artifact first. Every APA template includes a set of reps and warranties on intellectual property ownership and non-infringement (often labeled R1 through R4 in the standard form). Closeread's IP ownership artifact maps directly to those reps.

The reps are not negotiable. A seller who cannot honestly sign them either accepts a lower price or watches the deal die. The artifact's job is to surface IP ownership issues before the seller signs.

## What this artifact covers

Three signals from the codebase:

1. **Repository license.** Presence and SPDX-classification of a `LICENSE` / `COPYING` / `NOTICE` file at the repo root. The license body is matched against canonical SPDX signatures (MIT, Apache-2.0, GPL-2.0/3.0, AGPL-3.0, LGPL-3.0, MPL-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0).
2. **Per-file SPDX headers and copyright lines.** Source files declaring `SPDX-License-Identifier: X` are aggregated; copyright lines (Copyright YYYY Name) are extracted. Cross-checks against the root license surface contamination.
3. **Copyleft escalation.** Any AGPL/GPL classification escalates to CRITICAL or HIGH per the rubric, because the buyer must accept the same copyleft obligation post-close.

## What this artifact does NOT cover

- Contributor IP assignment / CLA / DCO status. The artifact flags WHO contributed; the buyer's counsel still needs to see signed agreements. The key-person artifact (10) feeds the contributor list this artifact references.
- Trademark or patent disputes. Only license-and-copyright signals from the repository. Trademark conflicts and patent licensing live in legal diligence, not code audit.
- Runtime SaaS terms of service ("by using this product, the customer grants..."). That is a separate doc-level review.

## How the audit runs the IP ownership scan

Deterministic. Three passes:

1. **Walk repo root for license-bearing files** in canonical order (LICENSE, LICENSE.md, LICENSE.txt, License, License.md, License.txt, COPYING, COPYING.md, COPYING.txt, NOTICE, NOTICE.md, NOTICE.txt). Inode-dedupe for case-insensitive filesystems. First match wins for canonical classification.
2. **Match each license file's body** against SPDX signatures. Each SPDX shortname has a curated list of phrases; ALL phrases must match (conservative). Unmatched files are classified as "custom license, needs counsel review."
3. **Walk source files for SPDX-License-Identifier and Copyright headers.** Cap to first 20 lines per file (headers live near the top). Cross-check declared per-file license against root license; mismatches emit MEDIUM findings.

The artifact health score is a deterministic function of the finding severity mix.

## Severity rubric

- **CRITICAL**: AGPL-3.0 at repo root. The buyer must publish derivative works under the same license even if they only operate the software as a hosted service without redistributing it. This is the single largest deal-killer in indie SaaS M&A.
- **HIGH**: No LICENSE file at repo root, OR GPL-2.0/3.0 / LGPL-3.0 at root (less restrictive than AGPL but still copyleft).
- **MEDIUM**: LICENSE file present but its body does not match any standard SPDX signature ("custom" license, needs counsel review). OR an SPDX-License-Identifier in a source file disagrees with the root license (contamination signal).
- **LOW**: copyright headers reference contributors not in the current org's contributor list (potential dormant-contributor cluster; see artifact 10).

## What "good" looks like in the packet output

A clean IP ownership artifact has:

- LICENSE file at repo root, classifiable as a permissive SPDX-listed license (MIT, Apache-2.0, BSD-* preferred for commercial SaaS).
- All source files either declare the same SPDX header or have no header.
- Copyright lines all reference the seller's org (or named individuals with signed assignment agreements).
- A `NOTICE` file enumerating any third-party code incorporated under MIT/BSD/Apache that requires attribution.

A seller whose codebase has a clean IP ownership artifact can sign the standard APA IP reps without amendment. A seller with an AGPL repo cannot, period. The remediation path for AGPL is re-licensing, which requires consent from every contributor whose code is still in the tree. This can take weeks or block the deal entirely.

## The AGPL doctrine

AGPL is the single biggest deal-killer in this artifact. Most indie SaaS sellers are not aware of AGPL's scope: it triggers the copyleft obligation even on hosted-service use, not just on redistribution. A buyer who acquires an AGPL codebase must publish their entire modified source code, available to the SaaS's end users, on request. This is materially incompatible with most acquirers' business models.

If your repo is AGPL and you are considering listing for sale, the remediation order:

1. **Check if you are the sole contributor.** If yes, you can re-license to MIT or Apache-2.0 unilaterally. One commit + LICENSE update.
2. **If outside contributors exist**, contact each one for written re-license consent. Some will not respond. For contributors whose code is no longer in the tree (removed in some prior commit), you do not need their consent because their code is not part of the artifact you are selling.
3. **For unreachable contributors whose code IS still in the tree**, the choices are: rewrite their code, accept the AGPL contamination, or restructure the deal (asset purchase vs equity purchase, etc.). M&A counsel guides this.

## Detection caveats

- **Multi-license files.** A LICENSE file that combines multiple licenses (dual-license MIT + commercial; AGPL + commercial exception) needs counsel review. The scanner emits a MEDIUM finding noting the multi-match.
- **Blank first line in LICENSE.** Bug 10 in the Day 8 audit batch surfaced this; the post-fix scanner picks the first non-blank line as the canonical citation. No false-positive crashes.
- **Per-file SPDX headers in vendored code.** Many projects vendor third-party libraries with their original SPDX headers intact. The scanner flags the mismatch as MEDIUM ("contamination signal") even though the answer is usually "this is vendored, we know, see NOTICE." Sellers should pre-empt by adding `vendored/` paths to a `.spdxignore` or equivalent.
- **No LICENSE file but proprietary intent.** A repo with no LICENSE is, in most US jurisdictions, "all rights reserved." This is the default for closed-source SaaS but it is also a HIGH finding because buyer's counsel reads the absence as "the seller has not thought about IP at all," which is a sophistication signal.

## Recommended remediation order

For a seller preparing to list with non-trivial IP ownership findings:

1. **Add a LICENSE file at repo root.** For commercial SaaS, the standard choices are: MIT (buyer-friendliest, no obligations), Apache-2.0 (adds patent grant, slightly more buyer-restrictive but still permissive), proprietary with explicit "all rights reserved" + contributor assignment language (for closed-source). One commit.
2. **Add SPDX-License-Identifier headers to source files** going forward. Pre-commit hook can enforce. The retroactive backfill on existing files is optional but signals discipline.
3. **Send retroactive CLAs to past contributors** whose code is still in the tree. Most CLAs are 1-page emails: "I assign my contributions to <YourCo>; signed Name Date." Track the responses in your data room.
4. **For AGPL repos**, follow the AGPL doctrine above before any listing conversation.

## Related artifacts

- `10-key-person.md`: dormant contributors flagged there are the candidates whose CLA / assignment status this artifact needs reviewed.
- `03-sca.md`: SCA findings sometimes include packages whose licenses conflict with the root license (e.g. AGPL package imported into an MIT repo). The two artifacts cross-reference.
- The findings-library entries [no-license-file-or-non-osi-license.md](../findings-library/polyglot/no-license-file-or-non-osi-license.md) and [copyleft-license-without-source-headers.md](../findings-library/polyglot/copyleft-license-without-source-headers.md) cover the cross-cutting patterns.
