# Packet template

The canonical packet that ships to a customer at the end of a Closeread audit. Ten artifact zones, each answering a question a buyer's engineering team raises in their first hour with the codebase.

Each zone follows the same structure:

* **Heading** stating the zone and the buyer question it answers
* **Narrative summary** in plain English, two to four paragraphs
* **Findings table** listing every finding in the zone with severity, ID, summary, and citation
* **Per-finding detail block** for each finding: details, recommendation, effort, confidence
* **What this means for your buyer** section the seller can paste into their counterparty conversation
* **Out of scope** subsection naming what this zone did not cover

## The ten zones

| # | Zone | Buyer question |
|---|---|---|
| 1 | Reliability | How often does this break, and what does breakage look like |
| 2 | SCA | What dependencies does this carry, and what known vulnerabilities live in them |
| 3 | Stack | What languages and frameworks does this use, and how hard is it to hire for them |
| 4 | IP ownership | Who owns this code, under what license, and is there contamination |
| 5 | Architecture | How is the system organized, and where are the single points of failure |
| 6 | Third party | What external services does this depend on, and what is the vendor risk |
| 7 | Credentials | What secrets exist in the codebase, and what is the rotation posture |
| 8 | Security | What does standard static analysis surface, and what is the pre-pentest signal |
| 9 | Test coverage | What tests exist, and how much of the code do they actually exercise |
| 10 | Key person | Who has authored this code, and what is the bus factor |

## Finding schema

Every finding in every zone uses this schema:

```yaml
finding_id: FREE-NNNN
artifact: <one of: reliability sca stack ip_ownership architecture third_party credentials security test_coverage key_person>
severity: critical | high | medium | low | info
summary: A one-sentence statement of what was found. Under 200 characters.
details: The longer explanation of the finding, what it means in context, why it matters to a buyer.
citation:
  file: relative/path/to/the/file
  line_start: integer
  line_end: integer
  quoted_code: The verbatim code or text from the cited location.
recommendation: What the seller should do about this finding before listing.
effort: XS | S | M | L | XL
confidence: 0.0 to 1.0
is_sensitive: true if the citation contains a credential or other content that should be redacted in the rendered packet
```

The `citation` block is the load-bearing field. A finding without a verifiable citation does not ship. The Closeread pipeline runs a verifier pass that re-reads each cited location and drops any finding whose `quoted_code` does not appear at the cited file and line range; the open-source methodology asks contributors to apply the same discipline manually.

## Detailed zone documentation

The detailed shape of each zone, the standard checks within it, the typical findings to surface, and the typical false positives to suppress: shipping on the 30-day cadence after launch. The README at [`../methodology/`](../methodology/) tracks which zones are documented and which are planned.
