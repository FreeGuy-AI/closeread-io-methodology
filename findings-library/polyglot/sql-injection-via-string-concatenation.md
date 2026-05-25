---
finding_category: security
severity_observed: critical
remediation_effort: M
detection_method: hybrid
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 4/10 incidence)
---

# SQL injection via string concatenation in query construction

## What the audit found

Four audits in the same batch of ten. Different stacks (Node with raw `pg.query`, Python with raw `psycopg2.cursor.execute`, PHP with raw `PDO::query` despite PDO being available, Go with `database/sql.DB.Query`). The same pattern in every one: at least one query path constructed its SQL string by concatenating user-controlled input into the string body rather than parameterizing the inputs.

The variations were instructive:

- One Node repo had a search endpoint that built `\`SELECT * FROM products WHERE name LIKE '%${req.query.q}%'\`` directly into a template literal. The team had a parameterized helper available in the same file but had not used it on this path. The audit submitted `q=' OR 1=1 --` and watched the endpoint return the full product catalog including soft-deleted rows.
- One Python repo used `cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")` in an admin lookup tool. The tool was internal-only but reachable from any authenticated admin session. The audit demonstrated dropping arbitrary tables via a crafted email value.
- One PHP repo used `PDO::query("DELETE FROM sessions WHERE token = '$token'")` in a sign-out path. The session token came from a cookie. The audit forged a cookie value containing `' OR token IS NOT NULL --` and signed every active user out of the system in one request.
- One Go repo built a sort-order parameter into the query with `fmt.Sprintf("SELECT * FROM orders ORDER BY %s LIMIT 100", sortField)`. The `sortField` value was reflected from a URL query parameter. The audit demonstrated a UNION-based extraction of the `users` table's password-hash column through the sort parameter.

In all four cases the team had a parameterized-query mechanism available in the same codebase. The injection paths existed because someone had taken a shortcut on a specific line, not because the team did not know better at the architectural level.

## How the audit caught it

The security specialist runs a hybrid pass: static analysis to identify candidate paths, then dynamic confirmation against a deliberately-instrumented test database.

The static pass uses a Semgrep ruleset tuned for each language's database libraries. Rules fire on:

- String interpolation, template literals, or `+` concatenation inside the first argument to any known query function (`pg.query`, `psycopg2.cursor.execute`, `PDO::query`, `db.Query`, `db.Exec`, `cursor.execute`, `client.query`, `mysql.query`).
- `fmt.Sprintf` or `String.format` output passed as the first argument to a query call.
- Direct passage of `req.query.*`, `request.GET[...]`, `$_GET[...]`, or `r.URL.Query().Get(...)` into a query string body.

Each match emits a HIGH finding with the file path, line number, and the user-input source that reaches the sink.

The dynamic pass, when the deep audit includes live-endpoint checks and the seller has provided a test environment, sends a set of canary payloads (`' OR '1'='1`, `'; SELECT NULL --`, `' UNION SELECT NULL --`) to the identified endpoints and inspects responses for SQL-error signatures, response-time deltas indicating blind injection, or content changes indicating UNION success. A static-only finding is HIGH. Dynamic confirmation against any payload escalates to CRITICAL with a captured proof of exploitation.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, this is the classic OWASP A03 finding and has been on the top-10 list for two decades. Buyers' diligence teams will see a SQL-injection finding and read it as a baseline-hygiene failure. The team that ships a SQL-injection path in 2026 is signaling that its code-review process either does not exist or does not catch the most-documented vulnerability class in the industry. Every subsequent diligence question about secure-coding practices, code review discipline, and security training compounds the original finding.

Second, the data exposure. A successful SQL injection on any meaningful path typically grants the attacker read access to every table in the database the application user can reach, which is usually most or all of the application's data. Depending on the database engine and the application user's privileges, the attacker may also be able to write, drop, or escalate. The realistic dollar impact in a worst-case scenario (the injection is on a production endpoint, the application user has broad privileges, the attacker exfiltrates personal data subject to GDPR or HIPAA) is in the seven to eight figures: legal fees, regulatory fines, customer notification costs, credit monitoring, indemnification claims, and a public disclosure that affects the deal valuation directly.

Third, the audit-historical question. Buyers' diligence teams will ask whether the injection was ever exploited. The honest answer for most teams is "we do not know." SQL-injection exploitation typically leaves no abnormal application-log signature; the malicious query looks like a legitimate query to the logging layer. The seller is then in the position of representing "no known breach" without the evidence to back the representation, which slows the deal and often triggers a request for forensic review at the seller's expense.

## Recommended remediation

In order, all of these need to happen:

1. **Patch the specific path immediately.** Replace the string-concatenation construction with a parameterized query using the database library's standard mechanism: `$1, $2, ...` placeholders in pg, `?` placeholders in psycopg2 and most others, `PDO::prepare` with named parameters in PHP, `db.Query("... ?, ?", a, b)` in Go's `database/sql`. The fix is usually a one-line change per injection point.
2. **Sweep the entire codebase for the same pattern.** If one path used string concatenation, others probably do too. Use Semgrep with the same ruleset the audit used (publicly available at `semgrep.dev`) to find every instance.
3. **Audit historical query logs.** Where the database is configured to log slow or unusual queries, look for any historical query containing single-quote payloads, `UNION SELECT`, `OR 1=1`, or sleep-based timing patterns. Where the database is not configured to log, treat the lack of evidence as the answer it is, not as evidence of absence.
4. **Reduce the database user's privileges.** The application user almost never needs `DROP`, `TRUNCATE`, `ALTER`, or `CREATE` privileges in production. A least-privilege grant turns a future SQL-injection finding from "the attacker dropped the user table" into "the attacker could read but not modify."
5. **Add a Semgrep rule to CI.** The same ruleset the audit used can run in CI on every push, failing the build if any new query path matches the unsafe pattern. The first regression then surfaces as a failed build, not as an audit finding three years later.

## How the seller could have prevented this

The structural prevention is an ORM or query builder that does not expose a raw-string interface in the application code path. Prisma, Drizzle, SQLAlchemy with the core layer, Doctrine, GORM, ActiveRecord all force the developer to pass values as parameters rather than concatenate them into a query body. The team that uses one of these consistently does not produce SQL-injection findings in audits. The cost is the architectural commitment to the ORM (with its own tradeoffs around generated query quality and migration tooling); the benefit is that the entire OWASP A03 class disappears from the report.

The behavioral prevention, for teams that use raw query interfaces by design, is a code-review checklist with one line: "is any user input concatenated into a query string?" Reviewers reject any PR that introduces a concatenation. The discipline works for small teams and fails reliably at scale, which is why the structural prevention is the long-term answer.

The seller who has done neither faces a multi-day sweep through the codebase to find and patch every instance, plus the historical-audit conversation with the buyer's diligence team, plus the documented finding in the report regardless. The seller who has done the structural prevention arrives at exit with zero SQL-injection findings, a Semgrep CI scan showing no candidate paths in the last 12 months, and one fewer critical finding to negotiate in the schedule of representations.
