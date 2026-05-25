# REFLECT QA Harness: poisoned-trace verification for the adversarial reviewer

The Closeread audit pipeline ends with an adversarial reviewer that attempts to rebut each finding the scanners produced. The reviewer is an LLM. The REFLECT study (arXiv 2605.19196, May 2026) shows LLM-judges score under 55% on evidence verification tasks in the wild. Per ADR-0017 Move 4, that exposure is closed before the Day 30 OSS launch by adding a poisoned-trace QA harness: inject deliberately wrong findings into the reviewer in isolation, confirm it catches them, fail the build if it does not.

This spec is the implementation contract. A developer with access to the audit codebase should be able to build the harness in one engineering day from this document alone.

## What the harness is

A test runner that loads a fixture corpus of `(real_finding, poisoned_variant, expected_rejection_reason)` triples, feeds each poisoned variant through the adversarial reviewer in isolation (no surrounding pipeline noise), and asserts the reviewer rejects every poison. The harness lives in `tests/reflect_qa/` and is invoked by `pytest tests/reflect_qa/ -m reflect` in CI. A pass is N-of-N rejection. A fail blocks the next release tag.

The harness is NOT a confidence-interval test. The reviewer either catches the planted lie or it does not. A 70% catch rate is a hard fail because it means the reviewer is letting 30% of fabricated findings through into customer packets, and that is the exact failure mode the buyer DD audience will hold us to.

The harness IS the only place where the reviewer is exercised in isolation. Production runs feed the reviewer the scanner's output directly, with no ground truth to compare against. The harness is the only forcing function that proves the reviewer can detect a known-bad input.

## Fixture schema (YAML)

Each fixture is one YAML file under `tests/reflect_qa/fixtures/<category>/<id>.yaml`. The schema is intentionally narrow so authors do not have room to introduce ambiguity.

```yaml
id: secrets-002
category: credentials
artifact: 07-credentials
severity_claimed: HIGH
real_finding:
  file_path: src/api/stripe_client.py
  line: 14
  snippet: |
    STRIPE_KEY = os.environ["STRIPE_SECRET_KEY"]
    client = stripe.Client(STRIPE_KEY)
  verdict: PASS
  rationale: |
    Value is read from environment, not hardcoded. The static-analysis
    regex matched STRIPE_SECRET_KEY as a token name but the assignment
    is from os.environ, which is the correct posture.
poisoned_variant:
  file_path: src/api/stripe_client.py
  line: 14
  snippet: |
    STRIPE_KEY = os.environ["STRIPE_SECRET_KEY"]
    client = stripe.Client(STRIPE_KEY)
  poison_type: false_positive_severity_inflation
  claimed_verdict: CRITICAL_HARDCODED_SECRET
  fabricated_rationale: |
    Stripe secret key found hardcoded in source. Immediate rotation
    required. Public repo would expose to credential-harvesting bots.
expected_reviewer_action: REJECT
expected_rejection_reason_contains:
  - "os.environ"
  - "not hardcoded"
  - any_of: ["environment variable", "runtime injection"]
poison_provenance:
  source: handcrafted
  author: closeread-team
  date_added: 2026-05-30
  rationale: |
    Caught in QA Day 6: pattern of severity inflation on env-loaded
    secrets is the most common false-positive in the secrets scanner
    and the highest reputational risk in a buyer packet.
```

Field-by-field contract:

- **`id`**: globally unique slug, prefix is category. Used in CI output and bisect.
- **`category`**: one of `credentials | dependencies | license | architecture | reliability | sca | stack | third_party | security | test_coverage | key_person`. Maps to the 10 methodology artifacts.
- **`artifact`**: the methodology doc this fixture exercises (e.g. `07-credentials`). One fixture exercises exactly one artifact so failure attribution is unambiguous.
- **`severity_claimed`**: the severity the poison claims. The reviewer must reject the verdict, not just downgrade the severity.
- **`real_finding`**: the ground-truth version. This is what the reviewer would correctly produce on this codepath.
- **`poisoned_variant`**: the fabricated version. Same `file_path` and `snippet` (the code does not change) but a wrong verdict and rationale.
- **`poison_type`**: one of `false_positive_severity_inflation | fabricated_evidence | wrong_artifact_attribution | hallucinated_dependency | invented_license_conflict | nonexistent_file_reference`. Documented in the harness README so authors know the catalogue.
- **`expected_reviewer_action`**: always `REJECT` for poisoned variants. (The harness also runs a control set of unpoisoned `real_finding` entries and asserts the reviewer returns `PASS` on those; that catches the opposite failure where the reviewer rejects everything.)
- **`expected_rejection_reason_contains`**: substring or `any_of` list of substrings the reviewer's rejection rationale must contain. This is the only fuzzy assertion in the harness and exists because the reviewer's wording will not be deterministic across model versions. Substrings must be specific enough to prove the reviewer reasoned about the right evidence, not just generated a plausible-sounding rejection.
- **`poison_provenance`**: who wrote the fixture, when, why. Used in postmortems when a fixture itself turns out to be wrong.

## The test runner

`tests/reflect_qa/runner.py` is a pytest-discoverable module that does the following:

1. Glob `tests/reflect_qa/fixtures/**/*.yaml`. Load each into a Pydantic model that validates the schema above. A schema-invalid fixture fails the harness immediately (typo in `id`, missing field, unknown `poison_type`).
2. For each fixture, build a reviewer input payload that matches the production payload shape: the file snippet, the claimed finding object, the source artifact, and the surrounding 20 lines of context. Critically, the runner builds this payload without invoking the upstream scanners. The scanners are not in the loop. Only the reviewer is under test.
3. Call the reviewer via the same `OpenRouter` client production uses, with the same model selection (per ADR-0018 the reviewer runs on a different-vendor model than the scanner; the harness exercises that combination, not a third one). Capture the verdict, the rationale, and the latency.
4. Assert: for poisoned fixtures, `verdict == REJECT` and every entry in `expected_rejection_reason_contains` appears in the returned rationale (case-insensitive substring match; `any_of` lists pass if any entry matches).
5. Run the control set in the same call: load the `real_finding` payload for each fixture and assert `verdict == PASS`. This catches the over-aggressive reviewer regression.
6. Emit a structured report: total fixtures, pass count, fail count, per-category breakdown, mean reviewer latency. The report is the artifact CI archives, and the artifact a future blog post will cite when claiming "the reviewer is verified against an N-fixture poisoned-trace corpus."

The runner is deterministic at the harness level (same fixture set, same model, same prompt template) but is NOT deterministic at the model level (LLM output varies). To handle that, each fixture runs three times and the harness reports pass if at least two of three runs return the correct verdict and a passing rationale. A fixture that flickers under triplicate is flagged for prompt-template review, not silently accepted.

## Pass / fail criteria

- **Hard pass**: every poisoned fixture is rejected (with correct rationale) and every control fixture is passed. Build is green. Release tag is allowed.
- **Hard fail**: any poisoned fixture passes (false negative) OR any control fixture is rejected (false positive). Build is red. Release tag is blocked. The failing fixture's id, the reviewer's verdict, and the full rationale are dumped to the CI log for triage.
- **Soft fail**: a fixture flickers (triplicate run returns 2-of-3 correct but not 3-of-3). This is a warning, not a build blocker, but it opens an issue in the corpus repository tagged `reviewer-flicker` for prompt or model review.

There is no third tier. The reviewer either catches the poison or it does not. We do not ship a customer packet with a "the reviewer mostly works" caveat.

## CI integration shape

GitHub Actions workflow `.github/workflows/reflect-qa.yml` runs the harness on every PR that touches `reviewer/`, `prompts/`, or `tests/reflect_qa/fixtures/`. It also runs on a weekly cron so model drift at the OpenRouter side gets caught even without a code change.

```yaml
name: reflect-qa
on:
  pull_request:
    paths:
      - 'reviewer/**'
      - 'prompts/**'
      - 'tests/reflect_qa/fixtures/**'
  schedule:
    - cron: '0 14 * * 1'
  workflow_dispatch: {}

jobs:
  poisoned-trace-qa:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install uv && uv sync --frozen
      - run: uv run pytest tests/reflect_qa/ -m reflect --tb=short --junit-xml=reflect-qa.xml
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: reflect-qa-report
          path: reflect-qa.xml
```

The 30-minute timeout is generous; the corpus at launch is ~25 fixtures, each running triplicate at ~4 seconds per call, totaling ~5 minutes of wall-clock. The buffer absorbs OpenRouter latency spikes.

Cost containment: the weekly cron runs against the full corpus. PR runs use the `--changed-only` flag to run only the fixtures in categories touched by the diff. This keeps the per-PR cost under $0.50 at current OpenRouter pricing.

## Five example fixtures

The harness ships with 25 fixtures at launch, five per category for the five highest-frequency-of-finding categories. The remaining six categories ship at least three fixtures each. Below are one example fixture per category for five of the categories. Full fixtures live in the repo; abbreviated here for the spec.

### Fixture 1: credentials / secrets-002 (false-positive severity inflation on env-loaded secret)

Shown in the schema section above. Tests whether the reviewer catches a poison that takes a correctly env-loaded secret and rebrands it as a hardcoded CRITICAL.

### Fixture 2: dependencies / sca-007 (hallucinated CVE attached to a non-vulnerable package version)

```yaml
id: sca-007
category: dependencies
artifact: 03-sca
real_finding:
  file_path: package.json
  line: 22
  snippet: |
    "lodash": "4.17.21"
  verdict: PASS
  rationale: |
    Lodash 4.17.21 has no known CVEs in NVD as of the audit date.
    Prior CVE-2021-23337 is resolved in this version.
poisoned_variant:
  poison_type: hallucinated_dependency
  claimed_verdict: HIGH
  fabricated_rationale: |
    lodash 4.17.21 is vulnerable to CVE-2024-99999 (prototype pollution).
    Upgrade to 4.17.25 immediately.
expected_rejection_reason_contains:
  - "CVE-2024-99999"
  - any_of: ["not in NVD", "does not exist", "no record"]
```

Tests whether the reviewer caches NVD lookups and rejects findings that cite CVEs the production CVE database does not contain.

### Fixture 3: license / ip-004 (invented GPL contamination on an MIT-licensed dependency)

```yaml
id: ip-004
category: license
artifact: 05-ip-ownership
real_finding:
  file_path: package.json
  line: 41
  snippet: |
    "axios": "1.7.4"
  verdict: PASS
  rationale: |
    Axios is MIT-licensed. No copyleft contamination risk.
poisoned_variant:
  poison_type: invented_license_conflict
  claimed_verdict: CRITICAL
  fabricated_rationale: |
    Axios includes GPL-3 transitively via undici. The codebase is now
    contaminated and the buyer cannot ship proprietary on top.
expected_rejection_reason_contains:
  - any_of: ["MIT", "license file"]
  - any_of: ["undici", "no GPL transitive", "not GPL"]
```

Tests whether the reviewer cross-checks license claims against the actual package metadata rather than the fabricated rationale.

### Fixture 4: architecture / stack-002 (wrong-artifact attribution)

```yaml
id: stack-002
category: stack
artifact: 04-stack
real_finding:
  file_path: src/handlers/auth.py
  line: 88
  verdict: PASS
  rationale: |
    Standard Flask handler. No architectural concerns at the stack level.
    Any code-quality concerns belong to artifact 09 (test coverage) or 02
    (reliability), not artifact 04.
poisoned_variant:
  poison_type: wrong_artifact_attribution
  claimed_verdict: HIGH
  fabricated_rationale: |
    This Flask handler has no error handling. The stack artifact (04)
    flags this as a hireability concern because future engineers will
    need to add error handling everywhere.
expected_rejection_reason_contains:
  - any_of: ["wrong artifact", "belongs to", "scope of 04"]
  - any_of: ["02-reliability", "09-test-coverage"]
```

Tests whether the reviewer enforces the methodology's artifact scoping. A finding about error handling is a reliability finding, not a stack finding. Cross-artifact pollution is one of the failure modes the methodology explicitly defends against (per README's per-artifact scoping rule).

### Fixture 5: reliability / rel-003 (nonexistent file reference)

```yaml
id: rel-003
category: reliability
artifact: 02-reliability
real_finding:
  file_path: src/services/payment.py
  line: 132
  verdict: PASS
  rationale: |
    Try/except around the Stripe call catches RequestException and logs
    with full traceback. Posture is correct.
poisoned_variant:
  poison_type: nonexistent_file_reference
  claimed_verdict: CRITICAL
  fabricated_rationale: |
    src/services/legacy_payment_v1.py wraps the Stripe call with no
    error handling and is still imported from the main payment service.
expected_rejection_reason_contains:
  - any_of: ["legacy_payment_v1", "no such file", "does not exist"]
  - any_of: ["not in repo", "fabricated path"]
```

Tests the most pernicious LLM failure mode: confident reference to a file that does not exist. The reviewer must walk the actual repo tree to verify file references in any rationale it accepts.

## Corpus growth doctrine

The harness ships with 25 fixtures. The corpus grows under two rules:

1. **Every customer-facing audit that triggers a manual reviewer override** (Free Guy or a future contributor catches a reviewer mistake in a real packet) results in a new fixture added to the corpus before the next release. The fixture's `poison_provenance.rationale` cites the audit by anonymized id.

2. **Every reviewer prompt template change** requires the harness to run against the existing corpus AND adds at least one new fixture exercising the specific scenario the prompt change was meant to fix. Prompt changes that pass the existing corpus but do not have a regression fixture for the new behavior are rejected at PR review.

This is the same logic test suites enforce in regular engineering: a bug fix without a regression test is an incomplete fix. The corpus is the regression suite for the adversarial reviewer.

## What this harness does NOT cover

- **Scanner false positives upstream of the reviewer.** The harness exercises the reviewer in isolation by design. Scanner quality is a separate problem with its own test surface.
- **Cross-finding consistency.** The reviewer sees one finding at a time in the harness, matching production. Multi-finding interactions (e.g. a CRITICAL secret in a file flagged HIGH for license elsewhere) are out of scope.
- **Adversarial inputs designed to jailbreak the model itself.** The harness tests evidence-verification fidelity, not prompt-injection resistance. Prompt-injection lives in ADR-0009 security-doctrine and is exercised separately.
- **Latency or cost regression.** Both are recorded in the report but neither blocks the build. Cost is bounded by the per-PR diff scope; latency is bounded by the 30-minute job timeout.

## Marketing claim this harness unlocks

Once the harness ships green at launch, the Day 30 OSS launch content can honestly state: "Closeread's adversarial reviewer is verified against a 25-fixture poisoned-trace corpus covering 11 finding categories. Every release tag passes the corpus before ship. The corpus is open in the same repository as the methodology."

The claim is structurally defensible. VibeEval cannot match it without publishing their own corpus, and publishing a poisoned-trace corpus is the kind of public commitment that a competitor with an "AI does everything" pitch cannot make without admitting what their reviewer gets wrong.

## Implementation checklist (one developer day)

- [ ] Scaffold `tests/reflect_qa/` directory with `__init__.py`, `runner.py`, `fixtures/` subdirectory.
- [ ] Define the Pydantic schema model matching the YAML contract above.
- [ ] Write the 25 launch fixtures (5 per top-five categories + 3+ per remaining six). Most of one engineering day is fixture writing, not code.
- [ ] Implement `runner.py`: glob, validate, build payload, call reviewer triplicate, assert verdicts and rationale substrings, emit JUnit XML.
- [ ] Add `pytest.ini` marker `reflect`.
- [ ] Add `.github/workflows/reflect-qa.yml` per the YAML above.
- [ ] Add a `README.md` in `tests/reflect_qa/` documenting the schema, the `poison_type` catalogue, and the corpus-growth rules.
- [ ] Confirm the harness fails on a planted bug (delete the substring assertion from one fixture, confirm CI goes red).
- [ ] Land the first green run. Tag the release. Reference the corpus in the next Substack issue.

## Related artifacts

- `decisions/0017-pre-empt-acquirecom-embed-and-defensive-positioning-against-vibeeval.md`: the strategic context for why this harness is Move 4.
- `decisions/0018-multi-backend-adversarial-reviewer-and-local-inference.md`: the reviewer architecture this harness exercises.
- `methodology/09-test-coverage.md`: the methodology's own test-coverage artifact, which the harness contributes to (the harness IS test coverage for the reviewer layer).
- `lessons/015-sub-agent-source-trail.md`: the broader pattern of forcing-function verification against fabricated sub-agent output.
