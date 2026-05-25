# API Versioning Specialist: spec

The API Versioning Specialist answers the buyer DD question that lives one layer below "does this break in production": "if I ship a release tomorrow, do I take an existing client integration down with me?" Versioning hygiene is the codebase-readable signal of how cautiously the seller has treated their public surface area. A codebase with no versioning strategy, undocumented deprecations, and quietly-mutating response shapes is a codebase whose buyer inherits an unbounded customer-comms liability.

This spec is implementable in one to two engineer-days against the existing audit pipeline. It slots in beside the security and reliability specialists, consumes the same `Repository` input, and emits the same `Finding` shape.

## Scope

Three transport flavors, one shared rubric:

1. **REST.** Path-prefix versioning (`/v1/`, `/api/v2/`), header versioning (`Accept: application/vnd.example.v3+json`, `X-API-Version`), or query-param versioning (`?version=2`). At least one strategy must be present and consistent across the public surface.
2. **GraphQL.** Versioning is schema-evolution-based rather than path-based. The specialist checks for: schema files under version control, `@deprecated` directive usage with non-empty `reason` arguments, persisted-query manifests, and a documented schema-change policy.
3. **gRPC.** Versioning is package-namespace-based (`package myservice.v1;`). The specialist checks `.proto` files for explicit `vN` package suffixes, reserved field numbers on edited messages, and the presence of a buf or prototool config enforcing backward compatibility.

## Detection rules

Five finding shapes. Each maps to one or more transport flavors and one severity tier.

### Finding 1: missing-api-versioning-strategy

Triggers when the repository exposes HTTP routes, GraphQL endpoints, or gRPC services but no recognizable versioning strategy is present.

**REST detection.** Walk the project's route definitions (Express `app.get`, Flask `@app.route`, Django `urlpatterns`, FastAPI router, Rails `routes.rb`, Echo / Gin handler registrations, Phoenix router scopes, Laravel route files). For each registered path, check whether the path starts with `/v\d+/` or `/api/v\d+/`. If less than 60 percent of public routes match the prefix pattern, run a secondary scan for header-based or query-param-based versioning: search for any handler that reads `Accept`, `X-API-Version`, `Api-Version`, or a `version` query param within the first 20 lines of the handler body. If neither strategy is present, emit the finding.

**GraphQL detection.** Locate `.graphql` / `.gql` schema files or programmatic schema construction (`new GraphQLSchema(...)`, `makeExecutableSchema(...)`, `buildSchema(...)`, Apollo / Pothos / Strawberry / graphene). Versioning here is "is there ANY deprecation hygiene in the schema." Absence of `@deprecated` directive usage across a schema larger than 30 types is the proxy signal.

**gRPC detection.** Find `.proto` files. Parse the `package` declaration. Absence of a `vN` segment in the package name (e.g., `package myservice;` rather than `package myservice.v1;`) is the finding.

**Severity.** HIGH for public-facing repos (presence of a deployed-to-internet signal such as a `serverless.yml`, `vercel.json`, `wrangler.toml`, `Dockerfile` exposing a port, or a `*.commandcenter.consulting`-style domain in README). MEDIUM for internal / non-public repos.

### Finding 2: breaking-change-in-unversioned-endpoint

Triggers when an existing public endpoint has had its response shape changed in git history without a corresponding version bump.

**Detection.** For each public route detected in Finding 1, compute a stable identifier (HTTP method + normalized path). Run `git log --oneline -p -- <route-file>` and look for diffs that modify the response payload structure. Heuristic for "response shape change":

- Removed key in a returned object literal.
- Renamed key in a returned object literal.
- Type-changed value (string to number, scalar to array).
- Removed field from a Pydantic / TypeBox / Zod / Marshmallow / serializer schema referenced by the route.
- Removed field from a Protocol Buffer message in a `.proto` file (especially without a `reserved` directive on the field number).

For each shape-change diff, check whether the same commit introduces a new version path or a deprecation notice. If neither, emit the finding with the offending commit SHA, the route path, and the changed field.

**Severity.** CRITICAL if the change happened in the last 90 days on a public-facing repo. HIGH otherwise. LOW if the route file path is under `tests/`, `__tests__/`, or `fixtures/`.

### Finding 3: undocumented-deprecation

Triggers when a route, GraphQL field, or gRPC method is marked deprecated in code but the deprecation is invisible to API consumers.

**REST detection.** Look for handlers that contain the substring `deprecat` (case-insensitive) in comments, log statements, or response headers but do not set a `Deprecation:` HTTP response header (RFC 8594) AND do not appear in any file matching `CHANGELOG*`, `MIGRATION*`, `RELEASE_NOTES*`, or `docs/**/*deprecated*`.

**GraphQL detection.** Walk schema for fields marked `@deprecated`. Each `@deprecated` directive must have a non-empty `reason` argument that includes either a target removal date OR a migration path. `@deprecated(reason: "")` and `@deprecated(reason: "deprecated")` both emit the finding.

**gRPC detection.** Walk `.proto` for fields marked with the `deprecated = true` option. Same rule: the field must have a leading comment that includes a migration path OR a removal timeline.

**Severity.** HIGH on public-facing repos, MEDIUM otherwise.

### Finding 4: missing-rate-limiting-on-auth-endpoints

Triggers when authenticated routes do not appear to be rate-limited. This is an API-hygiene finding rather than a pure security finding because the buyer's question is "will a misbehaving client take this service down," which is the versioning specialist's territory (the security specialist covers auth-bypass and credential leakage separately).

**Detection.** Identify routes that require authentication: handlers that reference `req.user`, `current_user`, `@login_required`, `IsAuthenticated`, `Authorize`, `verify_jwt`, `passport.authenticate`, `requireAuth`, or equivalent ecosystem patterns. For each such route, check for rate-limit middleware applied at the route or at a parent router. Canonical libraries to recognize: `express-rate-limit`, `slowapi`, `django-ratelimit`, `Rack::Attack`, `golang.org/x/time/rate`, `redis-cell`, `bucket4j`, Cloudflare / API Gateway / Kong / Tyk middleware references in IaC. Absence of any rate-limit signal on a repo with more than three authenticated routes emits the finding.

**Severity.** HIGH for public-facing repos with auth routes touching payment, account-mutation, or password-reset paths (heuristic: route filename / path contains `payment`, `billing`, `password`, `reset`, `account`, `user`, `transfer`). MEDIUM for other authenticated routes. LOW for routes under `tests/` paths.

### Finding 5: missing-pagination-on-collection-endpoint

Triggers when a route returns a list / array / collection without a recognizable pagination contract.

**Detection.** Identify collection-returning routes by handler return shape: TypeScript `Promise<T[]>`, Python `List[Model]`, Go `[]Model`, a route handler whose final return reads a database with no `LIMIT` clause, an OpenAPI spec marking the response as `type: array`, or a GraphQL field whose return type is `[T!]!` without a Connection / Edge / Node wrapper.

For each collection-returning route, check for pagination parameters in the handler signature or in the route registration: `limit`, `offset`, `page`, `pageSize`, `cursor`, `after`, `before`, `first`, `last`. Absence of any pagination parameter emits the finding.

**Severity.** HIGH if the underlying data source is a database table that the same repo's migrations indicate has grown over time (presence of more than one migration referencing the table). MEDIUM if the data source is a small-cardinality enum / lookup table (heuristic: the route name contains `types`, `statuses`, `categories`, `roles`). LOW for tests fixtures or admin-only routes (path contains `admin`, `internal`).

## Finding shape

All five findings serialize into the canonical Closeread `Finding` schema. Excerpt:

```python
Finding(
    specialist="api_versioning",
    finding_id="missing-api-versioning-strategy",
    severity=Severity.HIGH,
    title="No versioning strategy detected on public REST surface",
    summary="34 public routes detected; none use path-prefix, header, or query-param versioning.",
    evidence=Evidence(
        files=["src/routes/users.ts", "src/routes/payments.ts"],
        commits=[],
        line_ranges=[("src/routes/users.ts", 12, 47)],
    ),
    remediation_hint="Adopt /v1/ path prefix for all public routes; document in API_VERSIONING.md.",
    references=["RFC 8594", "https://stripe.com/docs/api/versioning"],
    cross_refs=["08-security.md", "02-reliability.md"],
)
```

The `finding_id` field uses the five identifiers verbatim:

1. `missing-api-versioning-strategy`
2. `breaking-change-in-unversioned-endpoint`
3. `undocumented-deprecation`
4. `missing-rate-limiting-on-auth-endpoints`
5. `missing-pagination-on-collection-endpoint`

## LLM prompt template

Each deterministic scan produces a structured `RawFinding`. The LLM pass converts the raw findings into the packet-narrative-ready `Finding` with severity adjudication, evidence framing, and remediation hint. Prompt template below; substitute `{...}` placeholders at call time.

```
You are the API Versioning Specialist for the Closeread audit pipeline. You convert
raw scan output into a buyer-DD-ready finding with calibrated severity and a
remediation hint that a seller can act on in one engineer-day or less.

CONTEXT:
- Repository: {repo_name}
- Primary languages: {languages}
- Public-facing signal: {is_public_facing} (true if deploy config or public domain
  references found)
- Transport flavors detected: {transports} (rest, graphql, grpc)

RAW FINDING:
- id: {finding_id}
- title: {raw_title}
- triggering files: {files}
- triggering commits (if any): {commits}
- evidence snippet:
  ```
  {evidence_snippet}
  ```

YOUR TASK:
1. Set severity using this rubric, in order:
   - CRITICAL if a recent (within 90 days) breaking change is in production and
     the repo is public-facing.
   - HIGH if the finding affects the public API surface and is fixable but not
     yet fixed.
   - MEDIUM if internal-only or partially mitigated.
   - LOW if confined to test fixtures, admin paths, or low-traffic endpoints.
2. Write the `summary` field in one sentence, plain English, no hype words.
   Start with a quantified fact ("34 public routes detected; ...") not a
   qualitative judgment.
3. Write the `remediation_hint` in one to three sentences. Include the specific
   file or directory to edit and the canonical library or pattern to adopt.
   Estimate the engineer-day cost.
4. List up to three `references` that a remediation engineer should read. Prefer
   RFCs, the project's own existing patterns, and authoritative vendor docs over
   blog posts.
5. List up to three `cross_refs` to other Closeread methodology pages this
   finding interacts with.

CONSTRAINTS:
- No marketing language. No em dashes.
- Do not recommend tools the repo does not already depend on unless the
  remediation is impossible without one.
- If the raw evidence is ambiguous (e.g., a route file could not be parsed),
  set severity to INFO and explain the parse failure in the summary.

OUTPUT a single JSON object matching the Finding schema. No surrounding prose.
```

The prompt is intentionally short. The deterministic scan does the heavy lifting (identifying the route, the change, the missing strategy). The LLM only adjudicates severity and frames the narrative. This keeps the per-finding cost low and the audit cost predictable.

## What this specialist does NOT cover

- **API authentication correctness.** That is the security specialist's territory.
- **Performance of paginated endpoints.** The pagination finding only flags absence of pagination, not whether the implemented pagination scales.
- **OpenAPI spec correctness.** A separate specialist (proposed) covers spec-versus-implementation drift.
- **Schema registry hygiene for event-streaming APIs.** Kafka topic versioning, Avro schema evolution, and similar event-bus concerns are out of scope for v1 of this specialist.

## Implementation plan

Day 1, morning: implement the five deterministic scanners as standalone functions in `reference-cli/specialists/api_versioning.py`. Each returns a list of `RawFinding`. Use `tree-sitter` for route detection where available (Python, JS/TS, Go, Ruby); fall back to regex for the rest. Unit-test against the eight sample repos in `sample-set/` that have HTTP surfaces.

Day 1, afternoon: wire the LLM prompt template into the existing `Specialist.adjudicate(raw_findings)` interface. Reuse the model client and retry logic already present for the security specialist. Add a fixture-replay test harness so the prompt's behavior is reproducible without burning tokens on every CI run.

Day 2, morning: add the specialist to the pipeline registry, run end-to-end against three sample repos, and review the emitted findings against a hand-built ground-truth set. Tune the public-facing heuristic if false-positive rate exceeds 15 percent.

Day 2, afternoon: write the per-stack appendix entries (Python / FastAPI, Node / Express, Go / Echo, Ruby / Rails, PHP / Laravel) and update `methodology/README.md` to list the new specialist.

## Related methodology

- `02-reliability.md` cross-references this specialist when the breaking-change finding co-occurs with a missing error-path test for the affected route.
- `08-security.md` cross-references this specialist when the missing-rate-limit finding co-occurs with an authenticated route that touches credentials or PII.
- The findings-library will gain five new entries under `findings-library/polyglot/` keyed to the five finding identifiers above.
