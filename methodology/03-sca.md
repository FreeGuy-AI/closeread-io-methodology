# 03 SCA: software composition analysis

The buyer's first technical question on almost every SaaS acquisition is some version of "what known vulnerabilities live in this codebase's dependency tree?" SCA answers that question. It is the cheapest finding to produce and the most expensive finding to ignore.

A 50-line `npm audit` output and a 50-page commercial SCA report give the same buyer signal. The difference between them is the packaging around the data, not the data itself.

## What this artifact covers

The Closeread SCA artifact enumerates every declared dependency in every package manifest in the repository, queries [OSV.dev](https://osv.dev) for known advisories against each one, and emits one Finding per advisory. The supported manifests in v1:

- `package.json` and `package-lock.json` (npm)
- `requirements.txt` and `pyproject.toml` (Python PEP 621 + Poetry)
- `Gemfile.lock` (RubyGems)
- `go.mod` and `go.sum` (Go)
- `Cargo.toml` and `Cargo.lock` (Rust)
- `composer.json` and `composer.lock` (PHP)

Lockfiles take precedence over manifests when both exist (the lockfile has the resolved version; the manifest may have a range). Manifests are parsed for the declared range only when no lockfile is present.

## What this artifact does NOT cover

- Transitive deps not pinned in a lockfile. If you have `requirements.txt` with `requests>=2` and no lockfile, Closeread sees only `requests`, not the actual resolved version. The SCA finding will be informational rather than definitive in that case.
- Vulnerabilities in OS packages, container base images, or runtime dependencies that live outside the repository.
- Zero-days that have not yet been reported to OSV.dev. The methodology is honest about its source.
- Yanked / withdrawn advisories. The OSV.dev feed itself filters these; we trust the upstream filter.

## How the audit runs the SCA

Deterministic. The scanner walks every file in the repository whose name matches the supported manifests list, parses each one, deduplicates the `(ecosystem, package, version)` tuples, and dispatches an OSV.dev query per tuple. OSV.dev responses are stacked by severity (CRITICAL > HIGH > MEDIUM > LOW), deduplicated by GHSA ID across manifests, and emitted as one Finding per advisory.

Three reliability practices are non-negotiable for the SCA scanner:

1. **Per-manifest isolation.** A single malformed `package-lock.json` does not stop the rest of the manifests from being scanned. Each parse is wrapped in a try/except that captures and emits the parse failure as a separate INFO finding (the buyer sees "scanner could not parse X" rather than a silent miss).
2. **Bounded retry on OSV.dev failures.** OSV.dev occasionally drops connections mid-stream (`IncompleteRead`) on monorepos with 20-plus manifests. Each query retries up to 3 times with exponential backoff (0.5s / 1.0s / 2.0s) on transient errors (`RemoteProtocolError`, `Timeout`, `ConnectError`, 5xx). Never retries 4xx (the request itself is malformed; retrying wastes budget).
3. **Honest reporting on missing version data.** A finding with `version=None` (e.g. unpinned in requirements.txt) is emitted with the confidence dropped from 0.9 to 0.6 and the summary explicitly notes "(version not pinned)". The buyer should not infer false certainty from a finding whose source data is uncertain.

## Severity mapping

OSV.dev advisories carry a severity label in `database_specific.severity` for most ecosystems. Closeread maps these directly:

- `CRITICAL` -> `Severity.CRITICAL` (immediate rotation, fix before close)
- `HIGH` -> `Severity.HIGH` (fix before close)
- `MODERATE` / `MEDIUM` -> `Severity.MEDIUM` (fix in next sprint)
- `LOW` -> `Severity.LOW` (note in remediation log)
- Unlabeled / missing -> `Severity.MEDIUM` (default; manual review required)

The artifact's `health_score` is a deterministic function of the finding severity mix, not a model judgment. The same finding set always produces the same health score.

## What "good" looks like in the packet output

A clean SCA artifact shipping to a buyer has:

- Zero CRITICAL findings.
- Zero HIGH findings that lack a current patched version.
- MEDIUM findings with a clear remediation path (upgrade target, expected effort, deprecation deadline).
- A "what we did not cover" note naming any unsupported manifests in the repo (e.g. an SBT build for a Scala submodule we did not parse).

A seller who can hand a buyer this packet and answer "all HIGH and CRITICAL findings have been remediated within the last 30 days, here is the screenshot of the npm audit output today" has materially de-risked the deal at the technical-DD step.

## Detection caveats specific to ecosystems

- **npm**: the `package-lock.json` v1, v2, and v3 formats differ; the parser handles all three but the older v1 format is lossier (fewer integrity hashes). If your repo still uses npm v6, upgrade `npm` itself before listing.
- **PyPI**: `pyproject.toml` Poetry-style and PEP 621-style coexist; the parser handles both but the dep range syntax (`^1.0` vs `>=1.0,<2`) translates differently. We normalize to the OSV.dev format internally.
- **RubyGems**: only `Gemfile.lock` is parsed for definitive findings. `Gemfile` alone (no lockfile) emits informational findings with reduced confidence.
- **Go**: `go.sum` is the authoritative source. `go.mod` ranges alone do not constrain the version enough to query OSV reliably.
- **PHP / Composer**: same lockfile-precedence rule as npm.
- **Java / Maven / Gradle**: supported as best-effort; the dependency tree resolution differs across build tools. Treat findings here as conservative.

## Recommended remediation order

For a seller preparing to list with a non-trivial SCA backlog:

1. **Rotate any credentials referenced by a CRITICAL or HIGH advisory.** Some SCA findings (e.g. on auth libraries) indicate a credential that may have been exposed in the dependency's own vulnerability window.
2. **Patch CRITICAL findings** by upgrading to the published patched version. Run the regression test suite.
3. **Patch HIGH findings** the same way, in batches.
4. **Set up Dependabot or Renovate** to keep the dep tree current going forward. Document the policy in your data room so the buyer's team sees the cadence.
5. **MEDIUM and LOW findings** can ship un-remediated as long as they are documented in the data room with a stated remediation timeline.

## Related artifacts

- `04-stack.md` (TODO): the stack-and-hireability artifact references the same dependency tree but answers a different buyer question (how hard is it to hire engineers for this stack).
- `07-credentials.md` (TODO): the credential inventory artifact runs in parallel to SCA and can surface secrets that the SCA findings imply are compromised.
- The findings-library entry [out-of-date-dependencies-with-known-cves.md](../findings-library/polyglot/out-of-date-dependencies-with-known-cves.md) covers the cross-cutting pattern observed across the Closeread sample audits.
