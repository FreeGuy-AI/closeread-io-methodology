# Methodology

Eleven docs describe the Closeread approach. The philosophy doc is the only one a reader must read before deciding whether to use this methodology at all. The remaining ten are per-artifact, each mapped to one of the buyer DD questions Closeread answers in every packet.

Read in order, or skip directly to the artifact relevant to your situation.

| # | Doc | Buyer DD question | Reads in |
|---|---|---|---|
| 01 | [Philosophy](./01-philosophy.md) | Why audit before the buyer reads it first | ~8 min |
| 02 | [Reliability](./02-reliability.md) | How often does this break, and what does breakage look like | ~10 min |
| 03 | [SCA](./03-sca.md) | What dependencies does this carry, and what known vulnerabilities live in them | ~12 min |
| 04 | [Stack and hireability](./04-stack.md) | What languages and frameworks does this use, and how hard is it to hire for them | ~10 min |
| 05 | [IP ownership](./05-ip-ownership.md) | Who owns this code, under what license, and is there contamination | ~12 min |
| 06 | [Third party](./06-third-party.md) | What external services does this depend on, and what is the vendor risk | ~6 min |
| 07 | [Credentials](./07-credentials.md) | What secrets exist in the codebase, and what is the rotation posture | ~14 min |
| 08 | [Security](./08-security.md) | What does standard static analysis surface, and what is the pre-pentest signal | ~8 min |
| 09 | [Test coverage](./09-test-coverage.md) | What tests exist, and how much of the code do they actually exercise | ~8 min |
| 10 | [Key person](./10-key-person.md) | Who has authored this code, and what is the bus factor | ~10 min |

Per-stack appendices (Python, Node.js, PHP, Ruby, Go, Java, Rust, Elixir) live under [`../appendices-by-stack/`](../appendices-by-stack/) and are written so the methodology pages above stay language-agnostic.

The cross-cutting patterns Closeread has observed repeatedly across the public sample-packet set live in [`../findings-library/`](../findings-library/). Each entry is anonymized + cross-referenced to the methodology page that surfaces it.

Total methodology reading time: roughly 95 minutes if you read every page. Most readers only need 01 + the 2-3 artifact pages closest to their domain.
