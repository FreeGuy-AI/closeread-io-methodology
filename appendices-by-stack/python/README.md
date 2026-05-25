# Python appendix

Tools an auditor reaches for when the primary stack is Python, the typical false positives to suppress, and the minimum acceptable depth of coverage for a Closeread-grade packet on a Python codebase.

## Tools

| Zone | Tool | Notes |
|---|---|---|
| SCA | `pip-audit`, `safety`, `osv-scanner` | `pip-audit` and `safety` use different vulnerability databases; cross-reference. `osv-scanner` adds breadth. |
| Credentials | `gitleaks`, `trufflehog` | Same as Node. Watch for legacy `.env.example` patterns that look real. |
| Third party | manifest review + source grep | Parse `requirements.txt`, `pyproject.toml`, and `poetry.lock` against the vendor signature table. |
| Test coverage | `pytest --cov`, `coverage.py` | Almost universal in modern Python projects; check `pyproject.toml` for `[tool.pytest.ini_options]` or a `pytest.ini`. |
| Security | `bandit`, `semgrep --config=auto` | Bandit is the canonical Python static security linter; semgrep adds patterns Bandit misses. |
| Architecture | `pydeps`, manual `ast`-based import-graph review | Pydeps generates dependency graphs; `ast.parse` over source files reveals in-repo import edges. |

## Typical false positives

* `bandit` flags `assert` statements in test files (B101). Suppress with `--skip B101` for the test directory only, not globally.
* Generated migration files (Django, Alembic) often contain stringified SQL that bandit flags as injection risk. Confirm migrations are not user-input-driven before suppressing.
* `pip-audit` flags vulnerabilities in transitive deps that the application does not exercise. A clean packet names the transitive dep, the parent dep that requires it, and the runtime reachability assessment.
* `coverage.py` can report 100% on packages that have no real test surface if `--source` is mis-scoped. Verify the source scope before trusting the number.

## Minimum acceptable depth

* All six tools above run cleanly with no skipped checks on the most recent commit
* `bandit` runs with default severity and confidence settings; results capped at 8 high, 12 medium, 6 low in the packet to avoid finding-flood
* Test coverage measured, not assumed: actual percentage from `pytest --cov` or equivalent
* Architecture findings cite specific module names and `file:line` import statements; abstract diagrams without citations do not ship
