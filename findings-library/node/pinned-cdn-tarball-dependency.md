---
finding_category: sca
severity_observed: high
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized)
---

# Dependency pinned to vendor CDN tarball, bypassing the npm registry

## What the audit found

A Node codebase declared a spreadsheet-parsing library in `package.json` as a direct URL to the vendor's CDN, not as a semver range against the npm registry:

```
"xlsx": "https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz"
```

The version installed (0.20.3) carried a known prototype-pollution advisory that had been public for over a year. Because the dependency was pinned to a CDN URL rather than a registry version, `npm audit` did not flag it, the lockfile resolver did not auto-upgrade it on `npm install`, and the team's standard Dependabot rules did not see it.

## How the audit caught it

Deterministic, but with a small twist on the parsing side. The SCA specialist normalizes non-registry dependency declarations into `(package, version)` tuples before OSV lookup. URL-pinned and git-pinned dependencies are extracted and queried the same way registry-pinned ones are. This is one of the patterns that off-the-shelf `npm audit` misses by design.

## Why it matters to a buyer

Two compounding problems.

First, the underlying CVE is real and exploitable in the library's parsing path. That is a substantive finding.

Second, and worse for buyer trust: the seller's normal tooling **does not see** this dependency. The team can show a clean `npm audit` and a green Dependabot dashboard and have no idea that one of their parsers is on a year-old vulnerable build. A buyer reading the audit packet immediately asks "what other dependencies are pinned this way?" and the answer is usually "we don't know without looking." That answer reframes the entire SCA section of the data room from "audited and clean" to "audited only against the part of the dependency graph the tooling can see."

## Recommended remediation

1. Switch the CDN-tarball pin to a registry-version pin at the patched release. The vendor publishes to npm under the same package name; the CDN tarball was a historical workaround for unrelated reasons that no longer apply.
2. Grep the rest of `package.json` and any sibling workspace `package.json` files for the patterns `"http`, `"git+`, `"file:`, and `"link:` to find any other non-registry dependencies. Each one needs the same audit and migration.
3. Add a CI lint that fails the build if a `package.json` introduces a non-registry dependency without a comment explaining why.

## How the seller could have prevented this

The original engineer who switched to the CDN tarball almost certainly did so to solve a real, narrow problem (a typing issue, a version of the package that was not on npm at the time, a license preference). The fix that prevented this finding is not "never use CDN tarballs," it is "leave a comment when you do, and revisit the pin annually." The cost of the comment is 30 seconds. The cost of the audit finding at exit is several hundred thousand dollars in valuation hit.
