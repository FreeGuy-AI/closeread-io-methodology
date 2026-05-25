# Appendices by stack

Per-language guidance for running a Closeread audit against a specific stack. Each appendix is a focused doc that names the tools an auditor reaches for, the typical false positives to suppress, and the minimum acceptable depth of coverage for a Closeread-grade packet.

| Stack | Status | Folder |
|---|---|---|
| Node.js | shipping at launch | [`./node/`](./node/) |
| Python | shipping at launch | [`./python/`](./python/) |
| Ruby | 30 days post-launch | not yet |
| Go | shipping | [`./go/`](./go/) |
| PHP | 90 days post-launch | not yet |
| Elixir | shipping | [`./elixir/`](./elixir/) |
| Rust | shipping | [`./rust/`](./rust/) |
| Java/Kotlin | shipping | [`./java/`](./java/) |

## Contributing a new stack appendix

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md). Copy the Node or Python directory as a starting template and adapt the toolchain, false-positive list, and depth recommendations to your stack. Open an issue first if you want to discuss scope before writing.

The community-led stacks above are open. If you ship a working version that another operator validates against a real audit, it moves from experimental to reviewed.
