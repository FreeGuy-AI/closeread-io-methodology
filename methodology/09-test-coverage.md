# 09 Test coverage: what tests exist, and how much of the code do they actually exercise

The buyer's question is simple: "if I want to change something in this codebase post-close, will the test suite tell me when I break it?" The test coverage artifact answers this by measuring two signals: test count + actual line coverage.

A codebase with 1,000 tests and 80% coverage is a different artifact from a codebase with 1,000 tests and 12% coverage. Both look the same to a tool that counts test files; only the coverage measurement distinguishes them.

## What this artifact covers

Three signals:

1. **Test count and structure.** How many test functions exist, organized by canonical test framework (pytest, jest, mocha, rspec, gotest, JUnit, etc.).
2. **Coverage measurement.** Run the language's canonical coverage tool (coverage.py for Python, jest --coverage for JS, simplecov for Ruby, go test -cover for Go) and capture the line coverage percentage per artifact + overall.
3. **Test surface alignment.** What fraction of source files have a corresponding test file? A codebase with 200 source files and 5 test files is structurally undertested even if the 5 tests have 100% line coverage of what they touch.

## What this artifact does NOT cover

- Mutation testing or test quality assessment. Coverage measures line execution; it does not measure whether assertions are meaningful. A test that calls the function but asserts nothing achieves coverage without correctness.
- Integration / end-to-end test coverage that requires a running environment. The artifact runs unit tests only (the runnable-in-CI tier).
- Reliability-of-failure tests (e.g. `pytest.raises`). The reliability artifact (02) covers that signal separately.

## How the audit runs the test coverage scan

Deterministic, wraps existing tools. Per primary language:

1. Detect the test framework from manifest dependencies (`pytest` in `pyproject.toml`, `jest` in `package.json`, etc.).
2. Count test functions via AST-walk or canonical test-file naming convention.
3. Run the language's coverage tool against the test suite. Capture overall + per-file line coverage.
4. Compute test-surface alignment: fraction of source files with a corresponding test file (heuristic: `src/X.py` -> `tests/test_X.py` or `tests/X_test.py`).
5. Emit findings per the severity rubric.

If the coverage tool is missing or the test suite fails to run, the artifact emits an INFO finding and skips coverage measurement (test count is still reported).

## Severity rubric

- **CRITICAL**: line coverage under 10% on a codebase larger than 5,000 LOC. The test suite exists but is structurally inadequate.
- **HIGH**: line coverage between 10% and 30%, OR test count below 50 on a codebase larger than 10,000 LOC.
- **MEDIUM**: line coverage between 30% and 60%, OR test-surface alignment below 30% of source files having a corresponding test file.
- **LOW**: line coverage between 60% and 75%.
- **INFO**: line coverage above 75% (clean signal), OR coverage tool unavailable / test suite failed to run.

## What "good" looks like in the packet output

A clean test coverage artifact has line coverage above 75%, at least 100 test functions on any non-trivial codebase, test-surface alignment above 50%, and a CI configuration that runs the test suite on every PR. A seller who can hand a buyer this packet + a CI status badge has materially de-risked the maintainability conversation post-close.

## The coverage-vs-quality gap

A common seller mistake: optimize for the coverage number rather than the test quality. A 100% coverage test suite that uses `assert True` everywhere achieves the metric without delivering value. The artifact does not catch this; the buyer's engineering team will catch it during their walkthrough.

The honest signal a seller can offer: a smaller test suite with meaningful assertions + a coverage number that reflects only what is actually tested. 60% coverage with real assertions beats 100% coverage with mocked-everything tests.

## Recommended remediation order

For a seller preparing to list with low coverage:

1. **Stop chasing the percentage.** Focus on covering the highest-value paths (request handlers, payment flows, auth checks) first.
2. **Add error-path tests** for the top 20 production code paths. This raises coverage AND the reliability artifact (02) score simultaneously.
3. **Set up CI to enforce a coverage minimum** (start with whatever the current percentage is + a tolerance band; raise over time).
4. **Document the coverage policy** in the data room so the buyer sees the intent + cadence.

## Detection caveats

- **Generated code in the source tree** inflates the denominator. Coverage tools usually allow exclusions; the artifact respects standard patterns (`__pycache__`, `node_modules`, `vendor/`, etc.).
- **Integration / E2E test suites** are usually not run by the artifact because they require running environments. Sellers should note their existence in the packet narrative.
- **Mocked-everything test suites** show high coverage with low value. The artifact reports the number honestly; the buyer's team assesses quality.

## Related artifacts

- `02-reliability.md`: reliability scores test quality via failure-path coverage; this artifact scores test volume + line coverage. The two answer different questions.
- `08-security.md`: a codebase with low test coverage is more likely to have post-SAST regressions; the security artifact references this when relevant.
