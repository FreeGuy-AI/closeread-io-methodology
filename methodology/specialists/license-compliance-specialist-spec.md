# License Compliance Specialist: implementation spec

Sibling specialist to the IP-ownership artifact (`../05-ip-ownership.md`). Where IP-ownership scans the repo root and per-file headers of the seller's own code, the license-compliance specialist walks the **dependency tree** and flags license-level risks introduced by third-party packages. The two specialists run independently and cross-reference each other's findings.

This spec is implementation-grade. A developer working from this document should be able to build a working specialist in 1 to 2 days against the existing audit pipeline scaffolding.

## Scope and non-scope

In scope:

- Parse every supported package manifest in the repo and extract its declared direct + transitive dependencies (where the lockfile makes transitives available).
- Resolve each dependency's declared license to a canonical SPDX identifier.
- Flag conflicts between the repo's own license (read from the IP-ownership specialist's output) and the dependency tree.
- Flag missing license metadata in vendored deps, missing NOTICE-file attributions in production artifacts, and copyleft transitives in a SaaS context.

Out of scope:

- Patent grants, contributor license agreements (CLAs), or contributor IP-assignment chains. Those live with IP-ownership (root and per-file) and key-person (contributor identity).
- License compatibility legal opinion. The specialist surfaces the conflict; counsel decides whether the conflict is fatal.
- Runtime dynamic license enforcement (e.g. AGPL network-use trigger evaluation at execution time). Static manifest-level scan only.

## Inputs

The specialist consumes:

1. The repo path (read-only).
2. The IP-ownership specialist's emitted root license classification (SPDX shortname or `"unknown"` / `"custom"`).
3. The repo's declared product type (`saas` | `distributed-binary` | `oss-library` | `internal-tool`). Read from the audit's top-level `audit.yaml` config; falls back to `saas` when unspecified.
4. The optional `.licenseignore` file at repo root (one path glob per line) that lets the seller acknowledge vendored / pre-cleared directories the specialist should skip.

## Manifests it walks

Supported in v1, lockfile-precedence matches `03-sca.md`:

| Ecosystem | Manifest | Lockfile | License-field source |
|---|---|---|---|
| npm | `package.json` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` | `license` / `licenses` field per package |
| PyPI | `pyproject.toml`, `requirements.txt`, `setup.py` | `poetry.lock`, `Pipfile.lock` | PyPI JSON metadata (`info.license`, `classifiers`) |
| RubyGems | `Gemfile` | `Gemfile.lock` | RubyGems API (`spec.licenses`) |
| Cargo | `Cargo.toml` | `Cargo.lock` | crates.io API (`license`) |
| Go modules | `go.mod` | `go.sum` | best-effort via `go-licenses` if installed, otherwise pkg.go.dev scrape |
| Composer | `composer.json` | `composer.lock` | Packagist API (`license`) |
| Maven | `pom.xml` | (none) | `licenses` block in POM |

For each manifest the specialist emits a parse-success or parse-failure event so the packet narrative can name what was and was not scanned, matching the SCA artifact's honesty discipline.

## License resolution flow

For each `(ecosystem, package, version)` tuple the specialist:

1. **Reads the license field** from the manifest or the ecosystem's registry API. Common shapes: a single SPDX shortname (`"MIT"`), a SPDX expression (`"MIT OR Apache-2.0"`), a list (`["MIT", "Apache-2.0"]`), or a free-form string (`"BSD-style"`, `"see LICENSE.txt"`).
2. **Normalizes to SPDX.** A small lookup table maps common non-canonical strings (`"Apache 2"` -> `"Apache-2.0"`, `"BSD"` -> `"BSD-3-Clause"` with a confidence drop, `"MIT License"` -> `"MIT"`). Unmatched strings are classified `"unknown"` and emit a low-severity finding (the buyer's counsel still needs to review them).
3. **Records the resolution path.** Each resolved license carries a `source` field naming where it came from (`manifest` / `registry` / `lookup-table` / `unknown`) and a `confidence` float between 0 and 1.
4. **Categorizes the license** into one of: `permissive`, `weak-copyleft`, `strong-copyleft`, `network-copyleft`, `public-domain`, `proprietary`, `unknown`. The category drives the conflict logic in the next stage.

The resolution table for category assignment (canonical subset):

- `permissive`: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, 0BSD
- `weak-copyleft`: LGPL-2.1, LGPL-3.0, MPL-2.0, EPL-2.0
- `strong-copyleft`: GPL-2.0, GPL-3.0
- `network-copyleft`: AGPL-3.0, SSPL-1.0, BUSL-1.1 (treated as network-copyleft for risk purposes even though technically source-available)
- `public-domain`: CC0-1.0, WTFPL
- `proprietary`: anything matching a commercial-license pattern or named in the manifest as `"Commercial"` / `"Proprietary"` / `"UNLICENSED"`

## Conflict logic

The specialist emits findings when any of the following predicates fire. Each predicate maps to one finding shape (see next section). The repo's own license is read from the IP-ownership specialist's emitted root license; if that classification is `"unknown"` the conflict logic still runs but every finding's confidence drops by 0.2.

| Predicate | Finding shape | Severity |
|---|---|---|
| Strong-copyleft dependency in repo whose root license is permissive AND product type is `saas` OR `distributed-binary` | `gpl-contamination-in-permissive-codebase` | CRITICAL |
| Network-copyleft dependency in repo whose product type is `saas` | `network-copyleft-transitive-in-saas` | CRITICAL |
| Permissive dependency with no NOTICE / attribution file at repo root AND product type is `distributed-binary` | `missing-attribution-for-permissive-deps` | HIGH |
| Vendored directory (any dep under `vendor/`, `third_party/`, `extern/`, or a path matching the `.licenseignore` exception list) lacks an in-directory `LICENSE` / `COPYING` file | `vendored-dep-missing-license-file` | HIGH |
| Dependency's license resolved with confidence below 0.6 | `unknown-license-for-dependency` | MEDIUM |
| Repo root license is permissive AND a weak-copyleft dependency is present without per-file boundary documentation in NOTICE / README | `weak-copyleft-without-boundary-doc` | MEDIUM |
| Dependency in proprietary category present without a referenced commercial-license file at repo root | `proprietary-dep-without-commercial-license-doc` | HIGH |

The conflict logic is intentionally deterministic; no LLM is in the decision loop. The LLM only runs at the end of the pipeline to produce the human-readable narrative summary (see "Prompt template" below).

## Finding shapes the specialist emits

Each finding follows the audit pipeline's standard Finding schema (`category`, `severity`, `title`, `description`, `evidence`, `remediation`, `confidence`). The seven canonical shapes:

1. **`gpl-contamination-in-permissive-codebase`**. A GPL-2.0 or GPL-3.0 dependency exists in a codebase whose root license is permissive and whose product type ships as SaaS or distributed binary. The buyer must either remove the dependency, replace it with a permissive alternative, or accept GPL terms for the entire downstream product. Evidence cites the dependency name, version, manifest path, and resolved SPDX. Remediation lists at least one known permissive alternative when one exists (the specialist ships a small curated table of common replacements: GPL ImageMagick to MIT Sharp, GPL Readline to BSD-3-Clause editline, and so on). Severity CRITICAL.

2. **`network-copyleft-transitive-in-saas`**. An AGPL-3.0 / SSPL / BUSL dependency exists in a codebase whose product type is `saas`. The license triggers on hosted-service use even without redistribution, so the buyer inherits the obligation to publish source on request. Evidence cites the dependency, the dependency path from a direct dep (if transitive), and a note on whether the dep is being modified or used as-is. Severity CRITICAL.

3. **`missing-attribution-for-permissive-deps`**. The repo's product type is `distributed-binary` and at least one permissive dependency (MIT, BSD, Apache) is present, but no NOTICE / THIRD-PARTY-LICENSES / CREDITS file exists at repo root. The MIT, BSD-2/3, and Apache-2.0 licenses all require attribution in the distributed artifact. Evidence enumerates the deps that need attribution. Remediation suggests a generator (`license-checker --json` for npm, `cargo-about` for Rust, `go-licenses report` for Go) and a target file path. Severity HIGH.

4. **`vendored-dep-missing-license-file`**. A directory under `vendor/`, `third_party/`, or `extern/` (or any path the `.licenseignore` whitelists as vendored) contains source code but no `LICENSE`, `COPYING`, or `LICENSE.txt` file inside the directory. The buyer cannot verify the vendored code's license at all; the audit cannot resolve it either. Evidence cites the vendored-directory path and a sample of source-file names found there. Remediation: copy the upstream LICENSE file into the vendored directory at vendoring time. Severity HIGH.

5. **`unknown-license-for-dependency`**. A dependency's license could not be resolved with confidence > 0.6 (the registry returned an empty field, the manifest declared a non-SPDX string the lookup table could not classify, or the dep is hosted in a private registry the specialist cannot reach). Evidence cites the dependency, the raw license string (if any), and the resolution-confidence value. Remediation: ask the upstream maintainer to clarify, or read the upstream LICENSE manually and add a `.licenseignore` entry with the resolved classification. Severity MEDIUM.

6. **`weak-copyleft-without-boundary-doc`**. A weak-copyleft dependency (LGPL, MPL, EPL) is present in a permissive codebase, but the repo root has no NOTICE or README section documenting the dynamic-linking / file-boundary requirement that the weak-copyleft license imposes. Evidence cites the dep and the missing documentation. Remediation: add a NOTICE section explaining which weak-copyleft deps are dynamically-linked vs file-isolated. Severity MEDIUM.

7. **`proprietary-dep-without-commercial-license-doc`**. A dependency resolved as proprietary / commercial / UNLICENSED is present, but the repo root has no referenced commercial-license file. The buyer cannot verify that the seller has paid for or has rights to use the proprietary dependency. Evidence cites the dep and the manifest path. Remediation: add the commercial license file to the repo (or a pointer to where it is stored) and reference it in the NOTICE / README. Severity HIGH.

## Severity scale

Matches the broader Closeread Severity enum. Per-finding severity is set deterministically by the conflict logic in the table above. Test-path downgrade (if the offending manifest is under `tests/` / `fixtures/`) is applied last and drops the severity one level (CRITICAL -> HIGH, HIGH -> MEDIUM, etc.). Findings with confidence below 0.5 are downgraded one additional level.

The artifact health score is a deterministic function of the finding mix, identical in form to the IP-ownership artifact's score function. A single CRITICAL drops the score to 25 or lower; a HIGH drops it to 60 or lower; multiple MEDIUM findings drop it linearly.

## LLM prompt template

The LLM call is for narrative summary only, not for license expertise or judgment. The deterministic logic above produces the finding list; the prompt below converts that list into the artifact's `narrative` field that ships in the packet.

```
You are summarizing the license-compliance findings for a code audit.
You are NOT a license expert. You will be given a list of findings
already computed by deterministic logic. Your job is to write a 3 to 6
sentence narrative that a non-lawyer can read in 90 seconds.

Inputs:
  - product_type: {{ product_type }}
  - root_license: {{ root_license_spdx }}
  - findings: a JSON list, each element shaped:
      { category, severity, title, evidence, remediation }
  - total_dependencies_scanned: {{ n_deps }}
  - total_dependencies_unresolved: {{ n_unresolved }}

Output rules:
  - Plain prose, no markdown, no bullet points.
  - Lead with the single highest-severity finding by name.
  - Name the count of CRITICAL and HIGH findings.
  - Name the unresolved-dependency count if greater than 5% of total.
  - Do NOT speculate about whether a license conflict is legally fatal.
    Use language like "may require counsel review" rather than "is illegal."
  - Do NOT invent findings beyond the input list.
  - Do NOT recommend specific commercial outcomes (selling, pricing).
  - End with one sentence naming the remediation effort estimate from
    the findings list.

Length target: 90 to 150 words.
```

The prompt is deliberately scoped to summary writing. No license-interpretation responsibility is assigned to the model. If a finding requires legal judgment, the deterministic logic surfaces it; the prompt asks the model to repeat that surfacing, not to extend it.

## Implementation notes

- Reuse the SCA specialist's manifest-walker. The dependency-tree extraction is identical work; only the metadata fields read from each tuple differ (license vs. CVE).
- Cache registry API responses on disk for 24 hours. License metadata is effectively immutable per version, so cache invalidation is trivial.
- Run the seven predicates as a single pass over the resolved dep list. Each predicate is a pure function from `(dep, repo_license, product_type)` to `Optional[Finding]`.
- The `.licenseignore` parser uses the same glob library as `.gitignore` (e.g. `pathspec` in Python). Test it against repos that use both.
- For the curated permissive-alternative table (used in `gpl-contamination-in-permissive-codebase` remediation text), ship a small YAML file the developer can extend without code changes.
- Total expected implementation time: 1 to 2 days for a developer familiar with the audit pipeline scaffolding. Most of that is the registry API shims and the lookup tables; the conflict logic itself is under 200 lines.

## Related artifacts

- `../05-ip-ownership.md`: the repo-root-license specialist this one extends. The two specialists share input but emit non-overlapping findings.
- `../03-sca.md`: shares the manifest-walker code path. Findings are independent (vulnerabilities vs. licenses) but related (some CVEs are introduced by deps under licenses the seller did not realize they were inheriting).
- `../06-third-party.md`: the third-party vendor inventory references API SDKs; a few of those SDKs ship under non-permissive licenses, in which case the two specialists both emit on the same dep.
- `../../findings-library/polyglot/copyleft-license-without-source-headers.md`: the existing cross-cutting pattern for repo-level copyleft; the license-compliance specialist adds dependency-tree coverage on the same risk axis.
