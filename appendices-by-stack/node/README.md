# Node.js appendix

Tools an auditor reaches for when the primary stack is Node.js, the typical false positives to suppress, and the minimum acceptable depth of coverage for a Closeread-grade packet on a Node codebase.

## Tools

| Zone | Tool | Notes |
|---|---|---|
| SCA | `npm audit`, `osv-scanner` | Run both; cross-reference. `osv-scanner` catches what npm's own database misses on transitive deps. |
| Credentials | `gitleaks`, `trufflehog` | Gitleaks for breadth, Trufflehog for verifier-grade matches. |
| Third party | manifest review + source grep | Inventory dependencies in `package.json` against the vendor signature table. |
| Test coverage | `jest --coverage`, `c8`, `nyc` | Whichever the project uses. Look for a `coverage:` script in `package.json` first. |
| Security | `eslint-plugin-security`, `semgrep --config=auto` | Eslint plugin gives Node-idiomatic linting; semgrep adds polyglot SAST. |
| Architecture | `madge`, manual import-graph review | Madge produces a clean visualization of the dependency graph. |

## Typical false positives

* `npm audit` flags dev-only deps as high severity when they cannot reach production. Confirm `package.json` scopes before promoting. Suppress in the packet only with a written rationale.
* Test fixtures often contain example keys or fake tokens that look like credentials. Mark `is_sensitive: false` and add a note that the value is a fixture.
* Eslint security rules flag `eval` usage in build-time scripts (e.g. esbuild configs) where it is safe by construction. Suppress with `// eslint-disable-next-line` plus an inline comment that names why.

## Minimum acceptable depth

* All five tools above run cleanly with no skipped checks on the most recent commit
* Zero findings of severity `critical` shipped without a recommended remediation
* Test coverage measured, not assumed: actual percentage from a coverage run, not a file-count heuristic
* The third-party vendor inventory cross-references all dependencies declared in `package.json` and `package-lock.json` against the vendor signature table; any vendor not in the table gets a manual lookup before the packet ships
