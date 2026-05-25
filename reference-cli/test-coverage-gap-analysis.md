# Test Coverage Gap Analysis

**Generated:** 2026-05-25
**Scope:** `reference-cli/`, `findings-library/`, `packet-template/`, and the
`methodology/` spec files that generate testable contracts.

---

## State of current coverage

Zero test files exist in the repository. The CI workflow (`ci.yml`) runs
`pytest --collect-only` on both MCP packages and explicitly marks each step
`continue-on-error: true` with a comment reading "Remove this line once real
tests exist." The packet-template smoke test in CI is the only passing
assertion today, and it tests four string-presence checks against a single
Markdown file.

The `tests/reflect_qa/` directory referenced in `methodology/reflect-qa-harness-spec.md`
does not exist yet. The `scripts/` directory exists but is empty.

There is no `pytest.ini`, no `conftest.py`, and no test marker configuration.

**Net coverage: 0% of executable code. 0% of finding-schema contracts.**

---

## Component inventory

| Component | Location | Language | Executable lines (est.) | Tests |
|---|---|---|---|---|
| `closeread-audit-mcp` server | `reference-cli/mcp-server/src/` | Python | ~200 | None |
| `closeread-verify-mcp` server | `reference-cli/verify-mcp/src/` | Python | ~180 | None |
| Findings library entries | `findings-library/**/*.md` | Markdown / schema | ~20 files | None |
| Packet template schema | `packet-template/README.md` | Markdown / YAML | 1 schema block | Smoke test only |
| REFLECT QA harness | (spec only) `methodology/reflect-qa-harness-spec.md` | Python (to be built) | 0 shipped | None |
| `ci.yml` lint scripts | inline shell | Bash | ~60 lines | None |
| Reviewer calibration study | (spec only) `methodology/reviewer-calibration-study-design.md` | Python (to be built) | 0 shipped | None |

---

## Prioritized gap list

Gaps are ordered by load-bearing risk to the audit product and to the Day 30
OSS launch claim that the pipeline is verifiable.

---

### Gap 1: Ed25519 signature verification core (`verify-mcp`: `_verify_soul_text`)

**Priority: 1 of 10 -- highest.**

`_verify_soul_text` is the cryptographic heart of the buyer-trust story. It
parses the multibase public key, verifies the Ed25519 signature over the
canonical soul text, and checks the SHA-256 fingerprint. A regression here
silently ships a verification failure as a passing result. The function is
also called live against a remote URL in `tool_verify_soul`, so the inner
logic must be unit-tested in isolation from network calls.

**Framework:** pytest. Test file: `reference-cli/verify-mcp/tests/test_verify_soul.py`.

**Fixture approach:** generate a real Ed25519 keypair with the `cryptography`
library inside the test, sign a minimal `.soul` fixture string, then assert
the function returns `{"valid": True}`. Negative cases: tampered signature,
wrong fingerprint, missing `z`-prefix, truncated public key (26 bytes instead
of 32). Each negative case must return `{"valid": False}` with a specific
`"error"` key. Six test functions cover the full decision tree.

---

### Gap 2: MCP JSON-RPC dispatch loop (`audit-mcp`: `handle_tools_call` + router)

**Priority: 2 of 10.**

The stdio loop in `main()` is the only integration surface a Claude Code or
Cursor client will ever hit. The `handle_tools_call` router dispatches on the
`name` string to one of three tools. An unknown tool name must return
`isError: True`; a valid name with a missing required argument must return
`isError: True`; a valid name with a non-directory `repo_path` must return
`isError: True`. None of these paths are tested. A contributor who refactors
the router can silently break the MCP contract with no test failure.

**Framework:** pytest. Test file: `reference-cli/mcp-server/tests/test_dispatch.py`.

**Fixture approach:** call `handle_tools_call` directly (no subprocess, no
stdin/stdout). Pass constructed `{"name": ..., "arguments": {...}}` dicts.
Assert return shape matches the MCP content-block schema
(`{"content": [{"type": "text", "text": ...}]}` or `{"isError": True, ...}`).
Mock `ingest_repo` and all scanner functions via `unittest.mock.patch` so
tests run without the `closeread` package installed. Eight test functions:
unknown tool, missing repo_path, non-directory path, missing artifact_kind,
unknown artifact_kind, `list_artifact_kinds` happy path, `audit_repo` happy
path (mocked scanners), `audit_artifact` happy path (mocked scanner).

---

### Gap 3: Finding ID extraction regex (`verify-mcp`: `tool_extract_packet_findings`)

**Priority: 3 of 10.**

`tool_extract_packet_findings` uses a regex (`###\s+(FREE-\d{4})[:\s]+(.+?)`)
to parse the audit packet Markdown format. The regex has two silent failure
modes: it misses findings whose heading uses a colon after the ID vs. a space,
and it truncates multi-line summaries to the first line without a test
confirming that is correct behavior. The 120-character truncation in the
display string is also untested. This function feeds `tool_compare_packets`,
so a regex regression propagates silently into the diff tool.

**Framework:** pytest. Test file: `reference-cli/verify-mcp/tests/test_extract_findings.py`.

**Fixture approach:** a constant string fixture that is a minimal audit packet
Markdown with 3 findings in known format. Assert finding count, assert
specific `finding_id` values present, assert summary truncation at exactly 120
chars, assert empty result on a file with no `FREE-NNNN` headings. Also test
the `packet_path not found` branch and the `.pdf` branch returning the
"not yet implemented" error.

---

### Gap 4: `tool_compare_packets` set arithmetic

**Priority: 4 of 10.**

`tool_compare_packets` calls `tool_extract_packet_findings` for each path and
then does set arithmetic (`a_ids - b_ids`, `b_ids - a_ids`, `a_ids & b_ids`).
The only way this function can silently regress is if the regex in
`extract_packet_findings` changes and the set arithmetic works on a different
corpus than expected. But the output format ("Only in A: 3 ['FREE-1001', ...]")
is also untested, and the truncation of the display list at 5 items is
undocumented behavior a contributor may remove. The "both packets extract
cleanly" guard path is also untested.

**Framework:** pytest. Test file: `reference-cli/verify-mcp/tests/test_compare_packets.py`.

**Fixture approach:** two in-memory Markdown strings (write them to `tmp_path`
using pytest's built-in fixture). Assert common count, assert only-in-A list,
assert only-in-B list. Add a case where one path does not exist and assert
`isError: True` propagates.

---

### Gap 5: Findings library frontmatter schema validation

**Priority: 5 of 10.**

Every `.md` file in `findings-library/` carries a YAML frontmatter block with
required keys: `finding_category`, `severity_observed`, `remediation_effort`,
`detection_method`, `anonymized`, `contributed_by`, `source_audit`. There is
no test that validates this schema. A contributor submitting a new finding
without the `anonymized: true` key, or with a misspelled `severity_observed`
value, gets no feedback from CI. The Day 30 OSS launch depends on public
contributors; this gap widens as the library grows.

**Framework:** pytest + `python-frontmatter` (add to a `tests/` extras group
in `pyproject.toml` at the repo root). Test file:
`tests/test_findings_library.py`.

**Fixture approach:** golden-file diff is not needed here -- this is a schema
assertion, not a content assertion. Glob all `.md` files under
`findings-library/`. For each: parse frontmatter with `python-frontmatter`,
assert all required keys are present, assert `severity_observed` is one of
`[critical, high, medium, low, info]`, assert `remediation_effort` is one of
`[XS, S, M, L, XL]`, assert `anonymized` is `true`. Fail with the file path
on any violation so a contributor knows exactly which file to fix.

---

### Gap 6: Packet template finding-schema snapshot

**Priority: 6 of 10.**

The `packet-template/README.md` contains the canonical YAML finding schema
block. The existing CI smoke test checks four string-presence conditions
(length, section heading, `finding_id`, `severity`). It does not check that
all required keys in the schema are present: `citation`, `recommendation`,
`effort`, `confidence`, `is_sensitive`. If a key is removed or renamed in a
refactor, existing buyers with parsers built to the published schema will
break, and the CI test will still pass.

**Framework:** pytest. Test file: `tests/test_packet_template.py`.

**Fixture approach:** snapshot test -- read `packet-template/README.md`,
extract the YAML code block between the first `yaml` fence and the closing
fence, parse it with `yaml.safe_load`, and assert each of the 10 required
field names is a key in the parsed object. This is not a golden-file diff; it
is a key-presence assertion against a static list so the test is both readable
and resistant to whitespace churn. Any new required field the methodology
adds to the schema must be added to the assertion list in the same PR.

---

### Gap 7: `tool_verify_soul` network isolation (verify-mcp)

**Priority: 7 of 10.**

`tool_verify_soul` calls `urllib.request.urlopen` with a 10-second timeout.
There is no test for the error path when the URL is unreachable (`Fetch failed:
...`). More importantly, there is no test that confirms the function does NOT
call the network when given a malformed URL scheme or a `file://` path, which
is a light SSRF-class risk from a local MCP tool that any contributor could
introduce. The happy-path integration test is also missing.

**Framework:** pytest with `unittest.mock.patch("urllib.request.urlopen")`.
Test file: `reference-cli/verify-mcp/tests/test_verify_soul_tool.py`.

**Fixture approach:** mock `urlopen` to return a context manager yielding a
fake `.soul` string built with the same keypair from Gap 1's fixture helper.
Assert `{"content": [...], "text": "Signature VALID..."}`. Add a second mock
that raises `urllib.error.URLError` and assert `{"isError": True, "content":
[{"type": "text", "text": "Fetch failed: ..."}]}`. Do not test live network
in CI; the live URL is already exercised by the `lychee` link check.

---

### Gap 8: `handle_initialize` and `tools/list` protocol responses

**Priority: 8 of 10.**

Both MCP servers' `handle_initialize` returns a hardcoded dict with
`"protocolVersion": "2024-11-05"`. If the MCP spec version bumps and a
contributor updates the string in one server but not the other, there is no
test that catches the divergence. Similarly, `handle_tools_list` returns a
list of tool objects; a contributor who adds a new tool to `SCANNER_REGISTRY`
without updating `handle_tools_list` leaves the tool undiscoverable with no
test failure.

**Framework:** pytest. Test file: `reference-cli/mcp-server/tests/test_protocol.py`
and `reference-cli/verify-mcp/tests/test_protocol.py`.

**Fixture approach:** call `handle_initialize({})` and assert
`result["protocolVersion"]` is a non-empty string. Call `handle_tools_list({})`
and assert the returned tool list has at least as many entries as the number
of dispatched tools in `handle_tools_call`. For `audit-mcp` specifically:
assert `list_artifact_kinds` is in the tool list AND is dispatched without
error, catching the registry-vs-list divergence.

---

### Gap 9: REFLECT QA harness scaffold (`tests/reflect_qa/`)

**Priority: 9 of 10.**

The harness spec (`methodology/reflect-qa-harness-spec.md`) is complete and
implementation-grade. The directory does not exist. The CI workflow references
`pytest tests/reflect_qa/ -m reflect` in `reflect-qa.yml`, which also does not
exist. The marketing claim on the Day 30 launch ("verified against a 25-fixture
poisoned-trace corpus") cannot be made until the harness ships green. This is
the highest-complexity gap in the list but is deprioritized to 9 because it
requires the adversarial reviewer to be callable, which is currently blocked on
ADR-0018 Phase 1.

**Framework:** pytest with the `reflect` marker. Framework: defined in the spec.
See `methodology/reflect-qa-harness-spec.md` for the full implementation
checklist. The contributor's first task is scaffolding `tests/reflect_qa/`,
writing `runner.py` with the Pydantic YAML schema, and adding 5 fixtures for
the `credentials` category before wiring the reviewer call.

---

### Gap 10: CI bin-script existence check (`bin/check-em-dash.sh`, `bin/check-brand-premise.sh`)

**Priority: 10 of 10.**

The `ci.yml` lint step references two shell scripts at `bin/check-em-dash.sh`
and `bin/check-brand-premise.sh`. Neither exists in the repository yet. The CI
step exits 1 if either script is missing, which means the lint job is currently
broken on a clean checkout. This is the most actionable gap in the list: a
contributor can fix it in under an hour without writing any test logic. Both are
simple bash+grep wrappers that require no external dependencies.

**Framework:** shell script + pytest invocation. Test file: none needed -- the
fix is to vendor the scripts and add them to the repo. The pytest layer to
add: a `tests/test_bin_scripts.py` that uses `subprocess.run` to call each
script against a known-bad Markdown file (containing an em dash) and asserts
exit code 1, then a known-clean file and asserts exit code 0. This turns the
CI dependency into a first-class tested contract.

---

## Test file scaffold summary

```
reference-cli/
  mcp-server/
    tests/
      __init__.py
      test_dispatch.py        # Gap 2 -- tool router, isError paths
      test_protocol.py        # Gap 8 -- initialize + tools/list responses
  verify-mcp/
    tests/
      __init__.py
      test_verify_soul.py     # Gap 1 -- Ed25519 core, no network
      test_verify_soul_tool.py  # Gap 7 -- tool wrapper, mocked urlopen
      test_extract_findings.py  # Gap 3 -- regex, truncation, error paths
      test_compare_packets.py   # Gap 4 -- set arithmetic, error propagation

tests/                        # repo-root test suite (framework: pytest)
  __init__.py
  test_findings_library.py    # Gap 5 -- frontmatter schema, all .md files
  test_packet_template.py     # Gap 6 -- finding schema key snapshot
  test_bin_scripts.py         # Gap 10 -- shell scripts exit-code contract

tests/reflect_qa/             # Gap 9 -- build after ADR-0018 Phase 1
  __init__.py
  runner.py
  fixtures/
    credentials/
    dependencies/
    license/
    architecture/
    reliability/
```

---

## Framework reference

| Layer | Framework | Notes |
|---|---|---|
| Python unit + integration | `pytest` | All Python gaps. `pip install pytest` is already in CI. |
| Ed25519 fixture generation | `cryptography` (already a dep of `verify-mcp`) | Use in `test_verify_soul.py`. |
| Frontmatter parsing | `python-frontmatter` | Add to repo-root `pyproject.toml` `[project.optional-dependencies.test]` |
| Findings library schema | pytest assertions (no extra dep) | Key-presence only, no golden file. |
| Packet template schema | `yaml.safe_load` (stdlib `tomllib` pattern) | No extra dep. |
| REFLECT harness | `pydantic` + `pytest` + `openrouter` client | Per spec. Not buildable until ADR-0018 Phase 1. |
| Bin scripts | `subprocess` inside pytest | Exit-code assertions only. |

---

## How to pick a gap and start

1. Pick any gap from 1 to 10.
2. Create the test file at the path shown in the scaffold table.
3. Add `pytest` as a test dep in the relevant `pyproject.toml` if not already
   present.
4. Run `pytest path/to/test_file.py -v` locally to confirm the test exists and
   fails before the implementation is written.
5. Write or fix the implementation until the test passes.
6. Remove `continue-on-error: true` from the matching CI step once the test
   passes on a clean checkout.

Gaps 1-4 and 7 are self-contained within the `reference-cli/` tree and do not
require any external dependency beyond what is already in the package's
`pyproject.toml`. Gaps 5-6 and 10 require a repo-root `tests/` directory and a
minimal `pyproject.toml` at the repo root (one does not currently exist).
Gap 9 is blocked; do not start it until ADR-0018 Phase 1 is marked complete.
