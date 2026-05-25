---
finding_category: third_party
severity_observed: info
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# Third-party vendor inventory with critical-path concentration mapped

## What the audit found

Across three audits in the same batch, the third-party-dependency specialist produced a clean vendor inventory in each case. The pattern that emerged across all three was the same shape:

- Total vendors detected: 3 to 6 per codebase
- Critical-path vendors (payments + auth + infra): 2 to 3 per codebase
- One vendor (typically a payments provider) consistently held the largest footprint by file reference count
- A comms vendor (email/transactional) was always present and usually had the lowest file-reference count

In one case the dataset was: payments (11 refs), data (10 refs), infra (9 refs), comms (4 refs), comms (4 refs), comms (1 ref). In another: infra (20 refs), payments (10 refs), AI (4 refs), comms (1 ref), auth (1 ref).

None of these surfaced any finding. The artifact's value is the inventory itself.

## How the audit caught it

Deterministic. The specialist runs three parallel passes:

1. Grep the source tree for a maintained list of vendor SDK import paths and package names (e.g. `stripe`, `@stripe/`, `import stripe`, `from "stripe"`).
2. Grep configuration files and environment variable templates for vendor-specific prefixes (`STRIPE_`, `SUPABASE_URL`, `OPENAI_API_KEY`).
3. Walk vendor-hosted webhook handlers and outbound HTTP call sites that match known vendor domains.

Each detection produces a `(vendor, category, file_reference_count)` tuple. The artifact aggregates into a single table sorted by reference count, with the critical-path categories (payments, auth, infrastructure) called out separately because those are the vendors the buyer cannot swap in the first 90 days post-close.

## Why it matters to a buyer

The audit's job here is not to flag a problem. It is to **save the buyer's technical DD lead the two weeks of grep work** that would otherwise happen between LOI and close.

Three buyer-side reads come out of this artifact:

1. **Vendor-swap cost estimation.** Each critical-path vendor has a swap cost in engineering weeks. Stripe-to-something-else is typically 6 to 12 weeks. Auth0-to-Cognito is typically 8 to 16 weeks. The buyer prices these into the integration plan.
2. **Vendor-risk concentration.** If the buyer already has a Stripe relationship and the seller is on Adyen, that is a swap on Day 30. If the seller is concentrated on a vendor the buyer has compliance concerns about, the buyer needs to know on Day 0, not Day 90.
3. **The seller's negotiating posture.** If the seller is on enterprise contracts with two of three critical vendors and the buyer is not, the seller may have favorable pricing the buyer can inherit. This is a positive surprise the buyer wants to discover in DD, not in the first quarterly review.

## Recommended remediation

None required. This artifact is the remediation. It exists to make the inventory legible.

If the seller wants to maximize the value of this section in the data room, two cheap additions:

1. **For each critical-path vendor, attach the current contract terms** (per-transaction pricing, monthly commit, contract end date, renewal terms). Buyer's commercial DD lead would otherwise spend a week extracting this.
2. **For each non-critical vendor, name the engineer who originally selected it** and the rationale. This sounds trivial. It is consistently the question buyer's technical DD asks third, after "what is your stack" and "who built it."

## How the seller could have prevented this

Not applicable. The artifact is informational, not corrective. The pattern across audits is that sellers are surprised by how complete and useful this single artifact is at the LOI stage. It is one of the rare audit outputs that is more valuable to the seller (who can use it as a data-room asset directly) than to the buyer (who would have built it eventually anyway).
