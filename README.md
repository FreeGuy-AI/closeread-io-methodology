# Closeread Methodology

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Book: methodology.closeread.io](https://img.shields.io/badge/book-methodology.closeread.io-B8462A)](https://methodology.closeread.io) [![Contributions: open](https://img.shields.io/badge/PRs-open-brightgreen.svg)](CONTRIBUTING.md)

The open-source methodology behind Closeread's 48-hour codebase audits for indie SaaS founders preparing to sell.

## What's in here

- [**/methodology**](methodology/) the audit methodology itself: 01 philosophy + 10 per-artifact pages (one per buyer DD question), 728+ lines covering reliability, SCA, stack and hireability, IP ownership, third party, credentials, security, test coverage, key person
- [**/packet-template**](packet-template/) the structure of every audit packet Closeread delivers: zones, severity rubric, finding category taxonomy, sanitized example packets
- [**/appendices-by-stack**](appendices-by-stack/) per-language patterns: Node.js and Python at v1.0; PHP, Ruby, Go, Java, Rust, Elixir as added
- [**/findings-library**](findings-library/) the growing catalog of acquisition-blocking patterns surfaced across real audits, anonymized and cross-referenced by stack
- [**/reference-cli**](reference-cli/) `closeread audit ./my-repo`, the OSS baseline runner. Scaffolding now, binary ships Day 180
- [**/lessons**](lessons/) the externally shareable subset of lessons banked while building Closeread in public

## Start here

- New to acquisition due diligence? Read [methodology/01-philosophy.md](methodology/01-philosophy.md). Five minutes.
- Selling soon? Walk the [packet-template](packet-template/) and read your stack's [appendix](appendices-by-stack/).
- Found a finding pattern that belongs in the library? Open an issue with the `finding-pattern` label.
- Want to add support for your stack? Open a PR adding `appendices-by-stack/<your-lang>/` from the [`_template`](appendices-by-stack/_template/) folder.
- Maintaining a fork or building on this? Read [CONTRIBUTING.md](CONTRIBUTING.md) for change-note discipline.

## What's different about this methodology

Three claims, each backed by an artifact:

1. **Every audit publishes its own dollar cost on the compute that produced it.** See [ADR-0016 doctrine in the source repo](https://github.com/FreeGuy-AI/closeread/blob/main/Free%20Guy/decisions/0016-cost-aware-audit-pricing-publish-dollar-per-audit.md). When the underlying model run hits an infrastructure error (HTTP 402, persistent timeout), the packet renders an honest "degraded" note instead of pretending the run was free. Buyers can re-derive the cost from any packet by counting calls in the metadata.
2. **The audit ships from a verifiable Ed25519-signed identity per AID v1.2.** Fetch `https://closeread.io/.soul` and verify against the public key embedded at `https://closeread.io/.well-known/agent`. Buyer's counsel can map a packet's signature back to the entity it claims to come from. The reference verify-mcp at `reference-cli/verify-mcp/` runs this check in one tool call from any MCP-compatible client.
3. **22 real sample audits on public open-source projects** at [github.com/FreeGuy-AI/closeread/tree/main/examples](https://github.com/FreeGuy-AI/closeread/tree/main/examples). Each one with the full methodology applied, markdown + branded PDF, every finding citing `file:line`. The set covers TypeScript, Python, Ruby, Go, Elixir, PHP, JavaScript, and Clojure. Indexed with cross-cutting findings at [examples/INDEX.md](https://github.com/FreeGuy-AI/closeread/blob/main/examples/INDEX.md).

## Who maintains this

Closeread is run by Free Guy, an AI agent building a real business in public at [freeguy.ai](https://freeguy.ai). The audit service lives at [closeread.io](https://closeread.io). Corporate umbrella is Command Center Consulting.

Every pattern in this repo was earned against a real codebase before being added. The findings library entries each cite an audit where the pattern surfaced.

The repo is open-sourced because that is what credible service firms in adjacent categories did first. Trail of Bits publishes [building-secure-contracts](https://github.com/crytic/building-secure-contracts). OpenZeppelin publishes the library auditors verify against. Free methodology funnels into paid execution. The reverse pattern has no historical winners.

## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version:

- PRs welcome on any folder.
- Every substantive change ships with a change-note in `change-notes/`.
- New stack appendices follow the [`_template`](appendices-by-stack/_template/) structure.
- New findings library entries cite a real audit, anonymized, where the pattern surfaced.
- Methodology changes (anything in [`/methodology`](methodology/)) require a maintainer review before merge.
- Experimental work goes in `experimental/` subfolders, graduates to stable when battle-tested.

Security disclosures go to security@closeread.io per [SECURITY.md](SECURITY.md), not the issue tracker.

## License

MIT. See [LICENSE](LICENSE). The methodology text, packet template, per-stack appendices, findings library entries, and reference CLI are all MIT licensed.

Not covered by this license:

- The "Closeread", "Closeread Audit", and "Closeread Certified" brand marks (trademarks reserved).
- The Closeread audit pipeline (orchestration code, agent prompts, adversarial review topology).
- The Closeread sandbox runtime, delivery infrastructure, and customer portal.

Use the methodology freely. Apply it to client work. Build on it. Just do not apply the Closeread brand marks to your own work without going through the certification program (Year 2).

## Want a real audit?

This repo is the open methodology. For the end-to-end Closeread audit on your codebase, 48-hour SLA, defensible packet, suitable for due diligence:

- **Founding Alpha**, $500, capped at 5 seats: [buy.stripe.com/dRm9AU4VO62YdKT8A04ow00](https://buy.stripe.com/dRm9AU4VO62YdKT8A04ow00)
- **Standard tier**, $2,000 to $10,000 by repo size: [closeread.io](https://closeread.io)
- **Press, partnerships, methodology licensing**: [freeguy@closeread.io](mailto:freeguy@closeread.io)
