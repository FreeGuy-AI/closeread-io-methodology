---
finding_category: security
severity_observed: critical
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 3/10 incidence)
---

# JWT verification accepts the `none` algorithm

## What the audit found

Three audits in the same batch of ten. Different stacks (Node with `jsonwebtoken`, Python with `pyjwt` 1.x, Java with a custom `nimbus-jose-jwt` wrapper), different teams, different threat models. The same pattern in every one: the JWT verification call path accepted a token whose header declared `alg: none`, meaning no signature was attached and the verifier was instructed to skip cryptographic validation.

The specific patterns:

- One Node service called `jwt.verify(token, secret)` with no `algorithms` option. The `jsonwebtoken` library's default behavior accepts whatever algorithm the token header declares, including `none`. The audit forged a token with `alg: none` and a payload claiming `sub: "admin@example.com"` and watched the service authenticate the request as the admin user.
- One Python service was pinned to `pyjwt==1.7.1`, which contains the known `none`-algorithm bypass that was patched in 2.0. The team had not upgraded the library since 2019. The audit reproduced the bypass against the staging environment.
- One Java service had a custom verifier wrapper that read the `alg` header from the token, switched on its value to select a verification routine, and had a fallthrough branch labeled `// TODO: handle none` that returned `true`. The TODO had been in the code for two years.

In all three cases the affected endpoint issued user sessions. In two of the three the audit demonstrated full account takeover with a forged token in under five minutes.

## How the audit caught it

The security specialist runs two passes for JWT handling.

The static pass walks the repository for known JWT library imports (`jsonwebtoken` in Node, `pyjwt` and `python-jose` in Python, `nimbus-jose-jwt` and `jjwt` in Java, `golang-jwt/jwt` in Go, `ruby-jwt` in Ruby) and inspects every call site for the verification function. A call that omits the `algorithms` (or equivalent) parameter, that passes a list including `none`, or that uses a custom verifier without algorithm pinning emits a HIGH finding. A pinned-version match against the public CVE database for `none`-algorithm bypasses (CVE-2015-9235, CVE-2022-29217, and several others) emits a CRITICAL finding.

The dynamic pass, when the deep audit includes live-endpoint checks, forges a test token with `alg: none`, an empty signature, and a clearly synthetic subject (`sub: closeread-audit-canary`). The forged token is sent to the production session-validation endpoint. A 2xx response, especially one that returns user-scoped data, is the dynamic confirmation that the bypass is live and exploitable. The audit captures the request-response pair as evidence.

Static-only finding: HIGH. Static-plus-dynamic confirmation: CRITICAL with a separate note on the account-takeover demonstration.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, this is account takeover. Not "could lead to" account takeover, not "raises the risk of" account takeover. The audit constructs a forged token claiming any subject, the server accepts it, and the attacker now holds an authenticated session as that subject. Every user, every admin, every service account whose identity the JWT represents is reachable to anyone who can send an HTTP request to the endpoint. The exploitation cost is one `curl` command.

Second, the disclosure cost. Buyers' diligence teams treat a demonstrated account-takeover finding as a deal-pause event. The seller will be asked to remediate before close, document the incident response, audit historical access logs for evidence of exploitation, and represent in the schedule that no breach occurred. The historical audit is often impossible because the bypass leaves no abnormal log signature (the forged token looks like a legitimate token to the application's logging layer). The representation then has to be qualified, which slows the deal.

Third, the regulatory exposure. If the affected service handles personal data subject to GDPR, CCPA, HIPAA, or any equivalent regime, an undetected breach window of two-plus years (the `pyjwt 1.7.1` case is a real example) opens the seller to retroactive notification obligations the buyer inherits at close. The realistic dollar impact, in the worst case, is in the seven figures: legal fees for the notification exercise, regulatory fines, customer churn from the disclosure, and a probable indemnification claim against the seller from the buyer. In the best case (no exploitation occurred and the audit catches it pre-close), the cost is a sub-day engineering fix and an awkward week in the data room.

## Recommended remediation

In order, all of these need to happen:

1. **Stop accepting the bypass.** Every JWT verification call site must pass an explicit algorithm list that excludes `none`. The list should match the algorithm used to sign the tokens (usually `RS256`, `ES256`, or `HS256`); never include `none` and never include "any" wildcards.
2. **Upgrade vulnerable libraries.** `pyjwt` to 2.0 or later, `jsonwebtoken` to 9.0 or later, `ruby-jwt` to 2.7 or later, `golang-jwt/jwt` to v5 or later. Pin minimum versions in the manifest so a future install cannot regress.
3. **Audit for forged tokens in historical logs.** Look for tokens with no signature segment, tokens with header algorithms outside the expected list, and any session-issuance log entry without a corresponding authentication-success entry. Document any abnormal findings as part of the data-room representation work.
4. **Rotate any signing key whose validation was bypassed.** If the bypass was a `none`-algorithm acceptance, the underlying keys are not compromised in the cryptographic sense, but the trust boundary they represent has been violated. Rotating closes the chapter and is a credible action for the data-room representation.
5. **Add a regression test.** A unit test that constructs a `none`-algorithm token and asserts the verification function rejects it. The test runs in CI on every change to the auth code path.

## How the seller could have prevented this

The structural prevention is to use a managed identity provider (Auth0, Clerk, AWS Cognito, Supabase Auth, Stack Auth) and never implement JWT verification in application code. Managed providers handle algorithm pinning, library updates, and the dozen other edge cases (`kid` rotation, JWKS caching, clock-skew tolerance, audience and issuer validation) that the average team gets wrong at least once. The cost is a per-seat or per-MAU fee and a vendor dependency; the benefit is that the entire class of JWT-verification findings disappears from the audit report.

The behavioral prevention, for teams implementing JWT verification themselves, is two things together: pin the verification call to an explicit algorithm list, and keep the JWT library on a Dependabot or Renovate cadence so library-level patches land within 30 days of release. Either alone is insufficient; both together cover the failure mode.

The seller who has done neither and now discovers a `none`-algorithm acceptance in the data room is in the worst diligence position the report can produce: a critical security finding with a working exploit and an open question about whether the bypass was ever used. The seller who has done the structural prevention arrives at exit with no findings against the JWT call path at all, because the seller never implemented JWT verification in the first place.
