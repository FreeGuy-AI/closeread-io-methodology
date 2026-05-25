# 02 Reliability: how often does this break, and what does breakage look like

The buyer's question is not "how often did this break in the last 30 days" (that is operational data they cannot verify from a code snapshot). The question is: "what does the codebase tell me about the seller's relationship with reliability as a practice?" Closeread's reliability artifact answers the second question, which is the answerable one.

## What this artifact covers

Three readable signals from the codebase that correlate to operational reliability:

1. **Error handling discipline.** What fraction of API surface handles errors explicitly vs. lets them propagate up to a top-level handler? What fraction of database calls is wrapped in transactions with explicit rollback paths? The patterns are stack-specific; the scanner uses ecosystem-appropriate heuristics (Python `try/except`, Go `err != nil`, JS Promise.catch, Ruby rescue, etc.).
2. **Test surface that targets failure paths.** Test count alone is not the metric (test coverage is the artifact 09 question). Reliability looks specifically at how many tests assert error behavior (`pytest.raises`, `expect(...).toThrow`, `assert_raises`, etc.) vs. happy-path-only tests. A codebase with 100% line coverage but zero error-path tests is fragile in production.
3. **Operational instrumentation.** Logging and metrics presence in production paths. The scanner looks for canonical libraries (Sentry, Datadog, OpenTelemetry, Prometheus client libs, log4j-style structured loggers) and a baseline rate of log statements per LOC in production code paths.

## What this artifact does NOT cover

- Actual uptime, MTTR, or incident counts. Those live in the data room (PagerDuty exports, Datadog dashboards), not the codebase. The packet's reliability artifact does NOT make claims about historical uptime numbers; it makes claims about codebase posture.
- Runtime performance. That is a separate engagement (load testing, profiling, latency analysis).
- Disaster recovery readiness. Backups, replication, multi-region failover are infrastructure-as-code questions; we look at the IaC if it lives in the repo, but the runtime DR posture itself is out of scope.
- Single-point-of-failure analysis at the runtime layer. The architecture artifact (05) covers module-graph SPoFs at the code layer.

## How the audit runs the reliability scan

Deterministic, no LLM. Three passes per language:

1. **Error-handling pass.** For each source file in the primary language, count the rate of try/except (or equivalent) blocks per 100 LOC. Compare against a stack-specific baseline (Python codebases average ~3 per 100 LOC; Go average ~12 due to explicit error returns; Node async/await averages ~5). Significant deviation downward emits a MEDIUM finding.
2. **Test-failure-path pass.** For each test file, count the rate of failure-asserting test functions vs. total test functions. A codebase with 200 tests and zero `pytest.raises` (or equivalent) emits a HIGH finding for "no error-path coverage."
3. **Instrumentation pass.** Walk imports + manifest dependencies for canonical observability libraries. Absence of any (Sentry, Datadog, OTel, Prometheus, etc.) on a production-facing repo emits a MEDIUM finding. Presence of a library with a sub-baseline rate of usage emits a LOW finding.

The artifact's health score is a deterministic function of which of the three passes produced findings. A clean repo (all three passes silent) lands at 100. A repo with one HIGH finding lands around 60. The score is not a model judgment; it is a deterministic rubric.

## Severity rubric specific to reliability

- **CRITICAL**: production code with explicit bare-`except: pass` or `catch { /* ignore */ }` blocks on the request-handling hot path. This is the "silently swallow customer-facing errors" anti-pattern and reads as deal-killer-class.
- **HIGH**: zero error-path tests in the test suite, OR no observability library present on a repo with public HTTP endpoints.
- **MEDIUM**: error-handling rate materially below the language baseline, OR observability library present but used on less than 10% of production code paths.
- **LOW**: spotty logging in non-critical paths, missing structured log format (plain string interpolation instead of JSON / key-value).

## What "good" looks like in the packet output

A clean reliability artifact has:

- Error-handling rate at or above the language baseline (note the baseline used).
- Test suite includes a meaningful fraction of failure-asserting tests (rule of thumb: 15-25% of test functions assert error behavior).
- At least one canonical observability library wired into production paths.
- A "what we did not cover" note explicitly naming uptime/MTTR/incident data as outside scope.

A seller who can hand a buyer a clean reliability artifact has materially de-risked the conversation about "what happens when this breaks." The buyer's engineering team still wants the PagerDuty exports, but the artifact says the codebase is built for breakage to be observable and recoverable.

## Detection caveats

- **Polyglot repos.** A repo with substantial Python AND TypeScript code gets two reliability sub-passes (one per primary language above a 10% LOC threshold). The artifact health is the worse of the two.
- **Generated code.** Protobuf-generated stubs, OpenAPI clients, ORM models, and similar generated files are excluded from the per-100-LOC denominator. The artifact only judges human-written code.
- **Test framework detection.** Each language has a canonical test framework (pytest, jest, mocha, rspec, gotest); some have multiple. The scanner detects the framework in use from manifest deps; if none is detected and the test count is zero, the artifact emits a MEDIUM "no test framework detected" finding which is also flagged separately in artifact 09 (test coverage).
- **Library detection vs library use.** A package.json that imports `@sentry/node` but never calls `Sentry.init()` in production code is a HIGH finding, not a clean signal. The scanner looks for actual instantiation, not just import presence.

## Recommended remediation order

For a seller preparing to list with a non-trivial reliability gap:

1. **Add a top-level error boundary** to the production HTTP layer. Most stacks have a canonical middleware (Express error middleware, Flask errorhandler, Rails rescue_from). One file change.
2. **Wire one observability library** (Sentry is the cheapest install). 30 minutes for the SDK + DSN + a smoke-test error.
3. **Add 5 to 10 error-path tests** that assert the system behaves correctly under known failure modes (database unreachable, third-party API timeout, auth token expired). Half a day.
4. **Replace any `except: pass` or `catch { ignore }` blocks** with at minimum a log statement, ideally a proper recovery path.

## Related artifacts

- `09-test-coverage.md` (TODO): covers test count + coverage percentage, the volume-side question. Reliability covers the failure-path-discipline-side question.
- `08-security.md` (TODO): silent error swallowing can also be a security finding (e.g. an auth-check that swallows an exception and grants access). The two artifacts cross-reference each other when relevant.
- The findings-library entry [single-author-100-percent-commit-share.md](../findings-library/polyglot/single-author-100-percent-commit-share.md) covers the secondary signal that a single-author codebase is harder to operate reliably even when the code itself is clean.
