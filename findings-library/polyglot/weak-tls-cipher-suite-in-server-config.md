---
finding_category: security
severity_observed: high
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 6/10 incidence)
---

# Weak TLS cipher suite in server config

## What the audit found

Six of ten audits in the batch shipped a server configuration (nginx, Apache, HAProxy, Caddy, an Express HTTPS listener, or a Go `tls.Config`) that explicitly enabled at least one cipher suite or protocol version retired by the IETF or marked weak by Mozilla's SSL configuration generator.

The specific patterns:

- Three repos had nginx configs with `ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;` still listing the deprecated TLS 1.0 and TLS 1.1 lines, both retired by IETF RFC 8996 in 2021.
- Two repos enabled the `RC4` or `3DES` family in their `ssl_ciphers` directive, both broken under modern attacks (Sweet32, BEAST, RC4 biases).
- One Go service constructed a `tls.Config{}` with no `MinVersion` set, leaving Go's default which permits TLS 1.0 negotiation by an attacker-controlled downgrade.
- One Node service used the `https.createServer` defaults without setting `secureOptions` or `minVersion`, with the same effect.

In every case the live endpoint was reachable from the open internet. In two cases the endpoint was the primary payment-flow API; in one it was the admin dashboard's session-issuance path.

## How the audit caught it

The security specialist runs two passes against TLS configuration.

The static pass walks the repository for nginx (`*.conf` with `ssl_protocols` or `ssl_ciphers`), Apache (`*.conf` with `SSLProtocol` or `SSLCipherSuite`), HAProxy (`bind ... ssl ciphers`), Caddy (`tls` directives), and code-level configurations (`tls.Config` in Go, `https.createServer` and `tls.createServer` in Node, `ssl.SSLContext` in Python, `OpenSSL::SSL::SSLContext` in Ruby). Any cipher or protocol on the Mozilla Modern or Intermediate "MUST NOT" list emits a HIGH finding.

The dynamic pass, when the deep audit includes a live-endpoint check, runs `testssl.sh` or the `sslyze` equivalent against the production hostname. The dynamic pass catches the case where the repository says one thing and the deployed server says another, which is most of them.

The finding lists the specific cipher or protocol observed, the year it was retired, and the named attack it enables. A static-only finding is HIGH; a static-plus-dynamic finding (the weak cipher is live on the production endpoint) is HIGH with a CRITICAL escalation note when the affected path handles authentication or payment data.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the compliance signal. PCI DSS 4.0 explicitly prohibits TLS 1.0 and TLS 1.1 on any path handling card data. A weak cipher on a payment endpoint is a documented finding in any QSA assessment and a flat-fail on PCI readiness. SOC2 trust-services criteria treat the same configuration as a deficiency under CC6.7. A buyer planning to keep enterprise customers needs the configuration fixed before the next compliance review.

Second, the downgrade risk. The most common exploitation path is not a direct attack on the weak cipher but a downgrade attack: the attacker intercepts the handshake, strips the strong cipher advertisements, and forces the server to negotiate the weak one. The server then completes a handshake the user's browser will quietly accept, and the attacker has the session in plaintext. Browsers have removed user-visible warnings for many of these conditions; the seller's customer would have no indication the connection was compromised.

Third, the regression cost. Removing TLS 1.0 and TLS 1.1 sometimes breaks one or two ancient enterprise customers running internal proxies pinned to old TLS. The seller who runs the audit and fixes the config has a controlled window to coordinate with those customers. The buyer who inherits the weak config and runs the audit post-close has the same conversation under deal-integration pressure, with the customer churn risk concentrated in the first 90 days. Realistic dollar impact: $5K to $20K of engineering and customer-success work to coordinate the cutover, plus any deal value lost from customers who cannot upgrade their integration in time.

## Recommended remediation

In order, all of these need to happen:

1. **Identify every TLS-terminating surface.** Web servers, load balancers, CDN edge configs, internal service mesh sidecars, and any application code that calls `tls.createServer` or equivalent. The audit's static pass produces the inventory.
2. **Set a single minimum version policy.** TLS 1.2 is the floor for any production-internet-facing surface in 2026; TLS 1.3 is the preferred default. Apply the policy uniformly. Mixed policies across surfaces are how regressions land.
3. **Replace the cipher list with a curated set.** Use the Mozilla SSL Configuration Generator output for the "Modern" or "Intermediate" profile, matched to the server software's actual version. Do not hand-curate cipher strings; the generator output is audited and updated as new attacks land.
4. **Confirm with a live scan.** Run `testssl.sh` or `sslyze` against every production endpoint after the change. The scan output is the artifact the buyer's diligence team will want to see in the data room.
5. **Add a CI check.** A weekly scheduled `testssl.sh` run against staging, with a failed-build threshold on any HIGH-severity grading, catches regressions before they reach production.

## How the seller could have prevented this

The structural prevention is to terminate TLS at a managed edge (Cloudflare, AWS CloudFront, GCP Load Balancer, Fastly) and let the edge negotiate ciphers with the client. The managed edge tracks IETF and browser changes faster than any individual team, and the seller inherits the upgrade cadence automatically. The cost is a small latency overhead and a contractual dependency on the edge provider.

The behavioral prevention, for teams terminating TLS themselves, is a calendar event every six months to rerun the Mozilla generator and update the config. Most teams that set this up correctly never see a weak-cipher finding because their config is regenerated faster than the recommendations change.

The seller who has done neither faces a quick fix on the file (single PR, usually under an hour) followed by the coordination work with any customers running on retired TLS versions. The seller who has done the structural prevention arrives at exit with a clean TLS finding, an `A+` testssl.sh grade on every production endpoint, and one fewer compliance gap to discuss in the data room.
