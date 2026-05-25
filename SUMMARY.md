# Summary

[Introduction](README.md)

# Methodology

- [Philosophy](methodology/01-philosophy.md)
- [Reliability](methodology/02-reliability.md)
- [SCA: software composition analysis](methodology/03-sca.md)
- [Stack and hireability](methodology/04-stack.md)
- [IP ownership](methodology/05-ip-ownership.md)
- [Third party](methodology/06-third-party.md)
- [Credentials](methodology/07-credentials.md)
- [Security](methodology/08-security.md)
- [Test coverage](methodology/09-test-coverage.md)
- [Key person](methodology/10-key-person.md)

# Packet Template

- [Overview](packet-template/README.md)

# Findings Library

- [Overview](findings-library/README.md)
- [Polyglot patterns](findings-library/polyglot/committed-env-file-in-repository.md)
  - [Committed .env file in repository](findings-library/polyglot/committed-env-file-in-repository.md)
  - [Copyleft license without source headers](findings-library/polyglot/copyleft-license-without-source-headers.md)
  - [Git submodule with broken remote](findings-library/polyglot/git-submodule-with-broken-remote.md)
  - [HTML test fixture credential noise](findings-library/polyglot/html-test-fixture-credential-noise.md)
  - [JWT with `none` algorithm accepted](findings-library/polyglot/jwt-with-none-algorithm-accepted.md)
  - [Missing CODEOWNERS file](findings-library/polyglot/missing-codeowners-file.md)
  - [Missing CORS allowlist, wildcard origin](findings-library/polyglot/missing-cors-allowlist-wildcard-origin.md)
  - [Missing SECURITY.md, no disclosure policy](findings-library/polyglot/missing-security-md-no-disclosure-policy.md)
  - [Monorepo without CODEOWNERS per package](findings-library/polyglot/monorepo-without-codeowners-per-package.md)
  - [Niche stack language without hireability mitigation](findings-library/polyglot/niche-stack-language-without-hireability-mitigation.md)
  - [No LICENSE file or non-OSI license](findings-library/polyglot/no-license-file-or-non-osi-license.md)
  - [Out-of-date dependencies with known CVEs](findings-library/polyglot/out-of-date-dependencies-with-known-cves.md)
  - [Out-of-date package manifest with EOL runtime](findings-library/polyglot/out-of-date-package-manifest-with-eol-runtime.md)
  - [Secret in Dockerfile build arg](findings-library/polyglot/secret-in-dockerfile-build-arg.md)
  - [Secrets in git history not current tree](findings-library/polyglot/secrets-in-git-history-not-current-tree.md)
  - [Shallow clone, bus factor inconclusive](findings-library/polyglot/shallow-clone-bus-factor-inconclusive.md)
  - [Single author 100% commit share](findings-library/polyglot/single-author-100-percent-commit-share.md)
  - [SQL injection via string concatenation](findings-library/polyglot/sql-injection-via-string-concatenation.md)
  - [Test coverage below 30% of source LOC](findings-library/polyglot/test-coverage-below-30-percent-of-source-loc.md)
  - [Third-party vendor inventory with critical-path concentration](findings-library/polyglot/third-party-vendor-inventory-with-critical-path-concentration.md)
  - [Weak TLS cipher suite in server config](findings-library/polyglot/weak-tls-cipher-suite-in-server-config.md)
  - [XSS via `dangerouslySetInnerHTML`](findings-library/polyglot/xss-via-dangerouslysetinnerhtml.md)
- [Node patterns](findings-library/node/committed-env-files-with-high-severity-secrets.md)
  - [Committed .env files with high-severity secrets](findings-library/node/committed-env-files-with-high-severity-secrets.md)
  - [High-entropy secret in production tRPC path](findings-library/node/high-entropy-secret-in-production-trpc-path.md)
  - [Pinned CDN tarball dependency](findings-library/node/pinned-cdn-tarball-dependency.md)
  - [Transitive CVE in meta-framework](findings-library/node/transitive-cve-in-meta-framework.md)
  - [Zero tests detected against quarter-million LOC](findings-library/node/zero-tests-detected-against-quarter-million-loc.md)

# Appendices by Stack

- [Overview](appendices-by-stack/README.md)
- [Node.js](appendices-by-stack/node/README.md)
- [Python](appendices-by-stack/python/README.md)
- [Ruby](appendices-by-stack/ruby/README.md)
- [Go](appendices-by-stack/go/README.md)
- [PHP](appendices-by-stack/php/README.md)
- [Elixir](appendices-by-stack/elixir/README.md)
- [Rust](appendices-by-stack/rust/README.md)
- [Java/Kotlin](appendices-by-stack/java/README.md)

# Reference CLI

- [closeread-audit-mcp](reference-cli/mcp-server/README.md)
- [closeread-verify-mcp](reference-cli/verify-mcp/README.md)

# Lessons

- [Overview](lessons/README.md)

---

# Project

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [License](LICENSE)
