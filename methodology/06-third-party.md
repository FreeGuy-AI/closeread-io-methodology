# 06 Third party: what external services does this depend on, and what is the vendor risk

The buyer's question is operational: "if Twilio doubles their pricing next quarter, can this product survive the cost shock? If Stripe deprecates an API the seller depends on, how much engineering time does the buyer have to allocate to migration?" The third-party artifact enumerates the dependencies so both numbers can be estimated.

## What this artifact covers

Three signals:

1. **API integration inventory.** Walk source code for canonical SDK imports (`stripe`, `twilio`, `aws-sdk`, `@sendgrid/mail`, `@anthropic-ai/sdk`, `openai`, `@vercel/postgres`, etc.) and runtime fetch calls to known third-party domains.
2. **Vendor concentration.** Count distinct vendors and surface any single-vendor concentration where one provider is critical-path for multiple product features (e.g. "Stripe handles payments AND auth AND email").
3. **Cost-exposure signal.** For each detected vendor, classify into pricing-elasticity tier (predictable per-unit; usage-spike-vulnerable; subscription-tier-vulnerable). Sellers who depend on usage-spike-vulnerable vendors should disclose runtime cost metrics in the data room.

## What this artifact does NOT cover

- Vendor financial health (is the vendor going to stay in business). That is news monitoring, not code audit.
- API quota / rate limit data. The artifact surfaces WHICH vendors are used; the seller's runtime ops data covers HOW MUCH.
- White-label or rebranded vendors. If the seller is using a third-party API behind their own brand, the artifact catches the SDK import but not the rebranding chain.

## How the audit runs the third-party scan

Deterministic. Walk imports + manifest dependencies for the curated vendor-SDK list. Walk source for URL patterns matching known third-party API endpoints. Aggregate by vendor. Emit one finding per critical-path vendor that exceeds the concentration threshold.

## Severity rubric

- **HIGH**: single vendor handles 3+ critical-path features (deal-killer concentration; usually Stripe-for-everything or Auth0-as-only-SSO).
- **MEDIUM**: vendor classified as usage-spike-vulnerable AND seller has no documented cost ceiling in the data room.
- **LOW**: minor vendor (one feature, easily replaceable, no concentration).
- **INFO**: vendor inventory only, no finding.

## What "good" looks like in the packet output

A clean third-party artifact has a complete vendor inventory, no single-vendor concentration above the threshold, and a stated cost-monitoring policy for any usage-spike-vulnerable vendors. A seller who proactively names their vendor list + monthly run-rate + alternative-vendor options has materially de-risked the post-close vendor-management conversation.

## Recommended remediation order

1. **Diversify any 3-feature-on-one-vendor case** before listing if commercially feasible. The most common one is Stripe-for-everything (payments + auth + email).
2. **Document cost-monitoring** policy for usage-spike-vulnerable vendors. The buyer reads the absence as "the seller is not watching cost."
3. **Surface vendor list in data room** with runtime cost over trailing 12 months per vendor.

## Related artifacts

- `03-sca.md`: SDK imports overlap with SCA findings when the SDK has a known CVE.
- `07-credentials.md`: third-party API keys are credentials; the credentials artifact surfaces the key, this artifact surfaces the dependency.
- The findings-library entry [third-party-vendor-inventory-with-critical-path-concentration.md](../findings-library/polyglot/third-party-vendor-inventory-with-critical-path-concentration.md) covers the cross-cutting pattern.
