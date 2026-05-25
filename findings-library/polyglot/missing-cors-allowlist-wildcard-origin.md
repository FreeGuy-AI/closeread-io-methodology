---
finding_category: security
severity_observed: high
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 7/10 incidence)
---

# Missing CORS allowlist, wildcard origin in production response

## What the audit found

Seven audits in the same batch of ten. Different stacks (Express, FastAPI, Rails, Laravel, Gin, ASP.NET), different team sizes, different threat models. The same pattern in every one: a production HTTP API response that included an `Access-Control-Allow-Origin: *` header, either statically configured or returned dynamically by middleware that echoed the request `Origin` header without validation.

The variations were instructive:

- Three repos used the stock CORS middleware in default-permissive mode (`cors()` in Express with no options, `from flask_cors import CORS; CORS(app)` in Flask, `Rack::Cors` with `origins '*'` in Rails). The developers shipped the middleware to silence the browser console error without ever reading the docs on what the defaults meant.
- Two repos paired the wildcard origin with `Access-Control-Allow-Credentials: true`. This combination is rejected by every modern browser as a known security antipattern, so the browser still blocks the request. The configuration was security theater that did not actually function, but it was still on the wire and still flagged.
- One repo dynamically echoed the request `Origin` header back as the response `Access-Control-Allow-Origin`, with no validation against an allowlist. This is the worst of the three: it works in the browser, it permits any origin to make credentialed requests, and it leaves the API surface trivially abusable by any phishing site or compromised third-party script.
- One repo had a careful allowlist for the production hostname but had left `localhost:3000` and `localhost:5173` in the list for development convenience. The dev-time entries shipped to production.

In four of the seven cases the affected endpoint was the session-issuance or token-refresh path. In one it was the payment-flow API. The wildcard was not on a static asset CDN where it would be defensible; it was on the routes that matter most.

## How the audit caught it

The security specialist runs two passes against CORS configuration.

The static pass walks the repository for the named CORS middleware (`cors` in Node, `flask_cors` and `fastapi.middleware.cors` in Python, `Rack::Cors` in Ruby, `gin-contrib/cors` and `rs/cors` in Go, the built-in attributes in ASP.NET) and parses the configuration value. A wildcard, a missing argument list, or a regex that matches any host emits a HIGH finding. A pairing of wildcard origin with credentials emits an additional INFO finding noting the configuration is browser-rejected and useless.

The dynamic pass, when the deep audit includes live-endpoint checks, sends a preflight `OPTIONS` request with a deliberately crafted `Origin: https://closeread-audit-canary.invalid` header and inspects the response. A response that includes `Access-Control-Allow-Origin: https://closeread-audit-canary.invalid` or `Access-Control-Allow-Origin: *` against an endpoint that also accepts credentials is the dynamic confirmation that the configuration is live, not just present in the repository.

A static-only finding is HIGH. A static-plus-dynamic finding on a credentialed endpoint is HIGH with a CRITICAL escalation note.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the exploitation primitive. A wildcard origin on a credentialed endpoint converts every cross-site request forgery (CSRF) defense the seller built into a no-op. Any attacker who can place JavaScript on a page the user visits (a malicious ad, a compromised third-party script, a forum post that renders untrusted HTML) can issue an authenticated request to the API and read the response. The seller's own CSRF token middleware does not protect against this attack because the attacker can fetch a fresh token via the same wildcard before issuing the privileged request.

Second, the compliance signal. OWASP API Security Top 10 calls out misconfigured CORS as a recurring high-severity class. SOC2 trust-services criteria treat origin validation as a baseline control under CC6.6. A buyer's diligence team will flag the wildcard the moment the audit lands, and a remediation commitment will appear in the schedule of representations.

Third, the cascading-fix cost. The fix itself is small: replace the wildcard with an explicit allowlist of production hostnames, remove credentials from the public CORS surface, and confirm with a dynamic scan. The cost is the coordination across every consumer of the API. If the seller has third-party integration partners, mobile SDKs, or embedded customer applications that rely on the permissive configuration, each consumer needs to be notified, tested against the tightened policy, and migrated. Realistic dollar impact: $2K to $10K of engineering work for the fix, plus the customer-success cost of any integration partner whose configuration breaks under the tightened policy.

## Recommended remediation

In order, all of these need to happen:

1. **Enumerate every consumer of the API.** Production web app, mobile app, partner integrations, embedded customer SDKs, internal admin tools. Each is a hostname or set of hostnames that needs to appear in the eventual allowlist.
2. **Build the explicit allowlist.** Production hostnames only. No wildcards, no regex that matches any subdomain unless every subdomain is genuinely first-party, no localhost entries. The allowlist lives in configuration, not in code.
3. **Replace the permissive middleware configuration.** Pass the allowlist explicitly. Set `credentials: true` only on the routes that genuinely need to issue or accept cookies and authorization headers. Static asset routes do not need credentials.
4. **Stage the cutover.** Deploy the tightened configuration to a staging environment first, run the dynamic scan, confirm the production allowlist matches what every consumer actually sends. Then ship to production behind a feature flag if the framework supports it.
5. **Add a CI check.** A scheduled `OPTIONS` probe against the production endpoints, asserting that an unauthorized origin receives no `Access-Control-Allow-Origin` header in the response, catches regressions before they reach customers.

## How the seller could have prevented this

The structural prevention is to terminate CORS at a managed edge (Cloudflare Workers, AWS API Gateway, GCP Apigee) with an explicit allowlist configured outside the application code. The application never has to think about CORS, and the allowlist is a single configuration object that lives in the same place as the rest of the edge policy.

The behavioral prevention, for teams handling CORS in the application, is a code-review rule that any CORS middleware change requires explicit hostname enumeration. Reviewers reject any PR that introduces a wildcard, a regex, or a localhost entry destined for production.

The seller who has done neither faces a half-day of engineering for the fix and a week of customer coordination for any integration partner whose configuration breaks under the tightened policy. The seller who has done the structural prevention arrives at exit with a clean CORS finding, an explicit allowlist documented in the data room, and one fewer high-severity finding in the buyer's diligence report.
