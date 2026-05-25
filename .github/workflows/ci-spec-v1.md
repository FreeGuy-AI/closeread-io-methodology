# CI Workflow Spec v1: `closeread-io-methodology`

**Written:** 2026-05-24 (Day 10)
**Status:** Approved for drop-in (see `ci.yml` sibling file)
**Author:** Free Guy sub-agent (Sonnet, Lesson-023 batch)

---

## Purpose

A single GitHub Actions workflow (`ci.yml`) that runs on every push and pull request to `main`. The workflow gates merges on seven check categories. It is the enforcement layer for the documentation and code quality rules the methodology repo already documents but does not yet enforce structurally.

The goal is a green-or-red signal in under three minutes wall clock on a standard GitHub-hosted runner (ubuntu-latest). Every check must be reproducible locally without GitHub infrastructure.

---

## Trigger scope

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

No scheduled runs. No deploy steps. CI only. Deployment to GitHub Pages (mdBook output) is a separate workflow not covered in this spec.

---

## Runner

`ubuntu-latest`. Python 3.12 via `actions/setup-python`. Node 20 via `actions/setup-node`. mdBook via the official `peaceiris/actions-mdbook` action. No self-hosted runners required.

---

## Job structure

Two jobs, not one monolithic job:

- **`lint`** -- fast static checks. Fails fast on style and linting violations so contributors get signal in under 60 seconds.
- **`test`** -- slower artifact checks. Runs after `lint` passes. Covers the mdBook build, link checking, and the packet smoke test.

Dependencies: `test` depends on `lint` (`needs: lint`). If `lint` fails the runner does not burn minutes on `test`.

---

## Check 1: Markdown linting (`lint` job)

**Tool:** `markdownlint-cli2` v0.13+

**What it checks:** All `.md` files in the repo root and subdirectories, excluding `book/` (generated output) and `node_modules/` (not present but defensive).

**Configuration file:** `.markdownlint.jsonc` at repo root. Create this file with the ruleset. Key overrides from the markdownlint default:

- `MD013` (line length): disabled. Long prose lines in methodology documents are intentional.
- `MD033` (inline HTML): disabled. The findings library uses a small amount of HTML in tables.
- `MD041` (first line should be heading): enabled. Every document must start with an H1.
- Everything else: default enabled state.

**Install:** `npm install --save-dev markdownlint-cli2` pinned to `@0.13.0`. Checked into `package.json` so local runs match CI exactly.

**Command:**
```sh
npx markdownlint-cli2 "**/*.md" "#book/**" "#node_modules/**"
```

**Failure behavior:** Exit code 1 with per-file violation list. The workflow step name is `Markdown lint` and `continue-on-error: false`.

---

## Check 2: Em-dash enforcement (`lint` job)

**Tool:** `bin/check-em-dash.sh`

**What it checks:** Every `.md` file in the repo for the U+2014 em dash and U+2013 en dash characters. Both are banned per the project writing rule.

**Setup:** The script must be vendored into `bin/check-em-dash.sh` at the repo root. It requires bash and grep only, no external dependencies. The script is a simple grep wrapper: scan all `.md` files for U+2014 (em dash) and U+2013 (en dash), exit 1 with file:line if any match. Inline the logic or vendor from `bin/` if you have a copy.

**Command:**
```sh
find . -name "*.md" \
  -not -path "./book/*" \
  -not -path "./node_modules/*" \
  | xargs bin/check-em-dash.sh
```

**Failure behavior:** Exit 1 with file name and line number for each match. Message: "Project rule: em dashes are banned."

**Note:** The script also flags en dashes. Both are violations.

---

## Check 3: Brand premise check (`lint` job)

**Tool:** `bin/check-brand-premise.sh`

**Scope:** Public-facing content only. Run against:
- `methodology/*.md`
- `findings-library/**/*.md`
- `packet-template/README.md`
- `README.md`

Do NOT run against `sample-set/`, `research/`, or internal spec files. Those are not public-facing deliverables and may legitimately discuss the brand from an analytical angle.

**What it checks:** Presence of 30+ forbidden phrases that smuggle human-review framing into the brand (e.g. "our experts," "manual review," "human reviewer"). See the script for the full list. The brand premise is that Closeread is AI-end-to-end.

**Command (one file at a time, exit-on-first-fail):**
```sh
for f in methodology/*.md findings-library/**/*.md packet-template/README.md README.md; do
  bin/check-brand-premise.sh "$f" || exit 1
done
```

Alternatively wrap in a helper that accumulates failures. The script takes one file argument; loop externally.

**Failure behavior:** Exit 1 with the drift phrase and the matching line context.

---

## Check 4: mdBook build (`test` job)

**Tool:** mdBook v0.4.40 via `peaceiris/actions-mdbook@v1`

**What it checks:** That the book compiles without errors from current `SUMMARY.md` and all linked files. A missing file in `SUMMARY.md` or a broken `src` reference breaks the build.

**Command:**
```sh
mdbook build
```

**Output:** Written to `book/` (per `book.toml`). Not uploaded as an artifact in CI unless a future deploy workflow requests it.

**Failure behavior:** mdBook exits 1 and prints the error (e.g. "chapter not found"). The step name is `mdBook build`.

**Important:** `book.toml` sets `create-missing = false`. Any file referenced in `SUMMARY.md` that does not exist on disk fails the build. This is intentional -- the CI enforces that the table of contents stays accurate.

---

## Check 5: Link checking (`test` job, after mdBook build)

**Tool:** `lychee` v0.15+ via `lycheeverse/lychee-action@v1`

**What it checks:** All links in the compiled `book/` HTML output (not the source `.md` files -- lychee on raw Markdown misses relative path resolution). Both internal links and external URLs.

**Allowlist (`.lycheeignore` file at repo root):**
```
# Placeholder and example URLs
https://closeread.io
https://freeguy.ai
https://github.com/closeread-io/methodology
https://github.com/FreeGuy-AI/closeread-io-methodology
# buy.stripe.com payment link (real but not always reachable from CI)
https://buy.stripe.com/
# LinkedIn URLs (rate-limited from CI runners)
https://www.linkedin.com/
https://linkedin.com/
# agent.ai (rate-limited)
https://agent.ai/
```

**Configuration:**
```yaml
- uses: lycheeverse/lychee-action@v1
  with:
    args: >
      --verbose
      --no-progress
      --exclude-path ./book/404.html
      --timeout 20
      --retry-wait-time 5
      --max-retries 2
      ./book/
    fail: true
```

**Failure behavior:** lychee exits 1 and lists broken links. If a link is flaky from CI (rate-limited external service), add it to `.lycheeignore` rather than setting `fail: false` globally.

---

## Check 6: Spell check (`lint` job)

**Tool:** `cspell` v8+ via `npx cspell`

**What it checks:** All `.md` files. Unknown words fail the check unless they are in the project dictionary.

**Project dictionary:** `.cspell.json` at repo root with a `words` array. Pre-populate with domain-specific terms that cspell does not know:

```json
{
  "version": "0.2",
  "language": "en",
  "ignorePaths": ["book/**", "node_modules/**", ".git/**"],
  "words": [
    "closeread",
    "freeguy",
    "mdbook",
    "lychee",
    "cspell",
    "markdownlint",
    "jsonc",
    "pyproject",
    "vitest",
    "pytest",
    "trpc",
    "monorepo",
    "codeowners",
    "hireability",
    "polyglot",
    "multibase",
    "semver",
    "tarball",
    "saas",
    "acquiree",
    "acquirer",
    "gazdecki",
    "copyleft",
    "SPDX",
    "sbom",
    "devdeps",
    "healthcheck",
    "CVEs"
  ]
}
```

**Command:**
```sh
npx cspell "**/*.md" --no-progress
```

**Failure behavior:** Exit 1 with file, line, and unknown word. Add legitimate technical terms to `.cspell.json` rather than disabling cspell globally.

---

## Check 7: Python test suite (`test` job)

**Scope:** `reference-cli/mcp-server/` and `reference-cli/verify-mcp/`. Both packages use setuptools with `pyproject.toml`. Neither has a `tests/` directory yet.

**Action for now:** Install both packages in editable mode and run `pytest --tb=short -q` from each package root. If no tests exist, pytest exits 0 with "no tests ran" (not an error by default). This is intentional -- the CI job scaffolds the test runner so contributors can add tests without touching the workflow.

**Commands:**
```sh
cd reference-cli/mcp-server
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pytest --tb=short -q || true  # no-fail until first test is written

cd ../../verify-mcp
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pytest --tb=short -q || true
```

When tests do exist, remove the `|| true` and set the step to fail on a nonzero exit.

**No vitest step is scaffolded** because there are no `.js` or `.ts` files in the repo currently. Add the vitest step when JS is introduced.

---

## Check 8: Packet smoke test (`test` job)

**What it checks:** That the packet template renders without errors against a fixture input and that the output matches a golden file (or at minimum does not crash).

**Current state:** The packet template is Markdown with a schema, not a code-generated artifact. A true "render and diff" requires the reference CLI to be functional. Since the reference CLI has no `render` command yet, this step is scaffolded as a no-op assertion:

```sh
# Smoke test: confirm packet template README is non-empty and well-formed
python3 -c "
import pathlib, sys
p = pathlib.Path('packet-template/README.md')
text = p.read_text()
assert len(text) > 500, 'packet-template/README.md is suspiciously short'
assert '## The ten zones' in text, 'zone table missing from packet template'
print('Packet template smoke test: PASS')
"
```

When the reference CLI gains a `render` command, replace this with:
```sh
closeread-audit render --fixture tests/fixtures/sample-repo.json \
  --out /tmp/smoke-output.md
diff tests/golden/smoke-output.golden.md /tmp/smoke-output.md
```

The golden file update path: run `closeread-audit render --update-golden` locally, commit the updated golden file, let CI verify the match on subsequent runs.

---

## Secrets and permissions

No secrets needed. No outbound network calls in `lint`. The `test` job makes outbound calls only in the link-check step (lychee), which uses a standard GitHub-hosted runner with default egress.

The `GITHUB_TOKEN` permission defaults are read-only. No write permissions needed for this workflow.

---

## The YAML workflow

The actual workflow file is the canonical deliverable. The spec above exists to explain the decisions. Drop `ci.yml` into `.github/workflows/` and it runs as described. The spec file stays for institutional memory but is not executed by anything.

---

## Passing on current repo state

The workflow will pass on the current repo state with two conditions:

1. **`.markdownlint.jsonc` must be created** (or markdownlint-cli2 will apply its default strict rules and likely fail on line length in methodology docs). Create it with `MD013: false` at minimum.

2. **`bin/check-em-dash.sh` and `bin/check-brand-premise.sh` must be vendored** into the repo's own `bin/` directory. Write them as simple bash+grep scripts (no external dependencies), make them executable, commit them.

3. **`.cspell.json` and `.lycheeignore` must be created** (included in the workflow YAML companion, created as part of the same commit).

Everything else (mdBook build, Python package installs, pytest with no tests) passes today without changes.

---

## Local reproduction

Every check in this workflow runs locally without Docker or GitHub infrastructure:

```sh
# Install tools once
npm install
pip install pytest

# Run individual checks
npx markdownlint-cli2 "**/*.md" "#book/**"
find . -name "*.md" -not -path "./book/*" | xargs bin/check-em-dash.sh
bin/check-brand-premise.sh README.md
mdbook build
npx cspell "**/*.md" --no-progress

# Run all via act (optional, requires Docker)
act -j lint
act -j test
```

The `act` tool is optional. All checks are standard CLI tools with no GitHub-specific behavior.
