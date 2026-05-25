# Rust appendix

Tools an auditor reaches for when the primary stack is Rust, the typical false positives to suppress, and the minimum acceptable depth of coverage for a Closeread-grade packet on a Rust codebase.

"Rust" in audit terms covers a wide spread. The dominant cases in acquisition-side diligence are async backend services (Axum, Actix-web, Rocket), Tokio-driven CLIs and daemons, embedded and WASM workloads (often `#![no_std]`), and the growing band of full-stack Leptos and Dioxus projects shipping to production. The toolchain is almost always Cargo with a committed `Cargo.lock`. Toolchain version is usually pinned via `rust-toolchain.toml` or `rust-toolchain` and managed through `rustup`. The audit posture changes meaningfully across `no_std` versus `std`, sync versus async, and pure-safe versus FFI-heavy codebases, but the toolchain below covers all of them.

## Tools

| Zone | Tool | Notes |
|---|---|---|
| SCA | `cargo audit`, `cargo deny`, `osv-scanner` | `cargo audit` reads `Cargo.lock` against the [RustSec Advisory Database](https://rustsec.org/) at `github.com/rustsec/advisory-db`. `cargo deny check advisories` covers the same DB with broader policy enforcement (bans, sources, licenses). `osv-scanner` cross-references against the OSV breadth that the Rust-only DB sometimes lags. Run all three. |
| Credentials | `gitleaks`, `trufflehog` | Same as Node and Python. Watch for `.env` files that shipped before `dotenvy` or `config-rs` was added, hardcoded API tokens in `tests/` and `examples/`, and `secrets.toml` patterns from `config-rs` users who never gitignored the file. |
| Third party | manifest review + source grep | Parse `Cargo.toml` (workspace and member crates) and `Cargo.lock` against the vendor signature table. The lock file is authoritative for transitive resolution. Workspace projects often have a root manifest plus N member manifests; all of them count. |
| Test coverage | `cargo tarpaulin`, `grcov`, `cargo llvm-cov` | `cargo tarpaulin` is the default for line coverage on Linux x86_64. `grcov` plus the `-Cinstrument-coverage` rustc flag works across more platforms (macOS, Windows, ARM). `cargo llvm-cov` is the newer wrapper that most modern projects have moved to in 2025-2026; check for it first. |
| Security | `cargo geiger`, `cargo deny check bans`, `semgrep --config=auto` | `cargo geiger` quantifies `unsafe` usage by crate, including transitive. `cargo deny` enforces banned-crate lists, source allowlists, and duplicate-version detection. Semgrep adds polyglot SAST patterns that pure-Rust tooling does not run. There is no Brakeman-class framework-aware SAST in the Rust ecosystem yet; combine `clippy::pedantic` with semgrep to close the gap. |
| License | `cargo deny check licenses`, `cargo about` | License metadata lives in each crate's `Cargo.toml` `license` field. `cargo deny check licenses` enforces an allowlist; `cargo about` generates the attribution report. Pull both, cross-reference against the project's stated license tier, and flag any GPL or AGPL cascade the author may not realize they inherited. |
| Architecture | `cargo modules`, `cargo depgraph`, manual `pub use` and `mod` grep | `cargo modules generate tree` surfaces the in-crate module structure; `cargo depgraph` produces the inter-crate dependency graph for workspace projects. For framework-shaped projects (Axum router definitions, Actix `App::new()` chains, Leptos component trees), grep the entry-point file plus the routing module to map request flow. |

## Edition and MSRV concerns

Rust's edition system (`2015`, `2018`, `2021`, `2024`) is declared per crate in `Cargo.toml` via the `edition` field. The audit should record the edition of every workspace member, not just the root. Edition 2024 went stable with Rust 1.85 (released February 2025); a codebase still on `edition = "2018"` in 2026 is not broken, but it signals a long-deferred upgrade and usually correlates with deferred toolchain upgrades elsewhere. The packet names the edition spread, the date of the last `cargo update`, and the rust-toolchain pin if present.

MSRV (Minimum Supported Rust Version) is declared in `Cargo.toml` via `rust-version`. A codebase that pins MSRV at 1.75 in 2026 is asserting that it does not use any feature stabilized after 1.75; the buyer's question is whether that assertion is honest. `cargo msrv verify` runs the project's tests against the declared MSRV to confirm. A missing `rust-version` field on a published-crate project is a finding (the crate may break on consumers' toolchains without warning). A missing `rust-version` field on an application binary is informational (binaries usually ship with their own toolchain pin).

The 2026 baseline that the rubric tracks: Rust 1.85 introduced edition 2024 and is the practical floor for new work. Rust 1.75 (December 2023) introduced `async fn` in traits without a workaround crate; codebases pinned below that line are paying a real ergonomics tax. Rust 1.65 (November 2022) introduced generic associated types; below that line the codebase is materially constrained. Each tier below current stable is a one-line note in the packet, not necessarily a finding.

## Tokio and runtime detection

Async Rust without a runtime is unusable in production. The packet identifies which runtime the codebase uses and which features are enabled. The signatures:

- `tokio` with `features = ["full"]` or `features = ["rt-multi-thread", "macros"]` is the dominant case. Production services almost always run on it.
- `async-std` is the historical alternative; most projects that started before 2022 may still use it. New code on `async-std` in 2026 is a finding (the project is on a runtime that is no longer the community default; hireability and maintenance posture both suffer).
- `smol` shows up in lightweight CLIs and tests. Often paired with `async-executor`.
- `embassy` is the embedded-async runtime; nearly always present alongside `#![no_std]` and a target like `thumbv7em-none-eabihf`.
- Custom runtimes built on `futures-executor` plus a hand-rolled reactor are findings until proven otherwise. The buyer's engineer will not have seen one before.

The Tokio version itself matters. Tokio 1.0 shipped December 2020; the 1.x line is API-stable. A project pinned at `tokio = "0.2"` or `"0.3"` in 2026 is on an unmaintained branch and the SCA findings will reflect that. Note the version in the architecture writeup, not just the SCA finding.

A second signature worth recording: whether the codebase uses `#[tokio::main]` (single-runtime, simplest case) or builds its own `Runtime` with custom thread-pool configuration (production tuning, often signals real load testing). The latter is a positive maturity signal in the packet narrative.

## Unsafe-block audit posture

The audit pass on `unsafe` in a Rust codebase is the single most stack-specific responsibility this appendix carries. Other Rust tooling exists; the human reading is non-delegable. The rules:

1. **`cargo geiger` runs first** and produces a per-crate unsafe-line count for the project and every transitive dependency. The packet quotes the project's own unsafe count and the top-three transitive offenders by unsafe-line count. A project at zero unsafe lines is the cleanest case; the realistic case is a non-zero count with documented justifications.
2. **Every `unsafe` block in the project's own code is read by hand**. Each block gets one of three labels in the packet: (a) FFI boundary, with the C ABI surface named; (b) performance optimization, with the safe alternative and the measured speedup named; (c) unjustified, requiring remediation. A clean packet has zero unjustified blocks or names them as findings.
3. **`unsafe impl Send`, `unsafe impl Sync`, and `unsafe trait` declarations** are surfaced separately from `unsafe { }` blocks because their failure mode is different (data race versus segfault). Each gets a hand-written justification in the packet.
4. **Transitive unsafe** is informational, not a finding by itself. Saying "this project uses `tokio` and `tokio` contains 2,400 unsafe lines" is not actionable; tokio's unsafe surface is audited by a large maintainer base. A finding fires only when a transitive crate with substantial unsafe usage has fewer than three active maintainers or has not seen a release in over 18 months.
5. **`#![forbid(unsafe_code)]` at the crate root** is a positive signal. Note it in the architecture writeup. A codebase that compiles with `forbid(unsafe_code)` and still calls into FFI has organized the FFI behind a single trusted-crate seam, which is the right pattern.

The unsafe audit is what separates a deterministic Rust scan from a Closeread-grade Rust packet. Deterministic tools count; the auditor reads.

## Secrets handling

Rust does not have a single canonical secrets-handling pattern the way Rails has `config/credentials.yml.enc`. The common patterns the auditor checks for:

- **`dotenvy`** (the maintained fork of the unmaintained `dotenv` crate) loads a `.env` file at startup. The audit confirms `.env` is in `.gitignore` and that `dotenvy::dotenv().ok()` is called early in `main()`. A `.env.example` file with placeholders is the documented pattern; flag any `.env.example` that contains real-looking values.
- **`config-rs`** builds a layered configuration from TOML/YAML/JSON files plus environment variables. The audit confirms that secret-bearing files (`secrets.toml`, `production.toml`) are in `.gitignore` and not present in git history. The layering order matters; env vars should override file values, not the other way around.
- **`envy`** deserializes environment variables into a struct via Serde. Lower-ceremony than `config-rs`; the audit just confirms `.env` discipline and that the struct has `#[serde(default)]` or fallback handling for missing values.
- **`secrecy`** wraps secret values in a `Secret<T>` type that prevents accidental `Debug` printing. The audit confirms that any field deserialized from `dotenvy` or `config-rs` that contains an API token, password, or signing key is wrapped in `Secret<String>` or `SecretBox<T>`, not passed around as a bare `String`.
- **Cloud-native secrets** (`aws-sdk-secretsmanager`, `google-cloud-secret-manager`, `vault-rs`) fetch secrets at runtime. Audit confirms that the credentials used to fetch the secrets themselves are not committed and that the runtime IAM role is the actual auth surface.

A codebase that does none of the above and passes secrets through bare environment variables in CI or via a `const API_KEY: &str = "..."` in source is a finding regardless of severity.

## Framework signatures

Framework detection in Rust is signature-based against `Cargo.toml` plus the entry-point source file. The signatures the auditor confirms:

- **Axum**: `axum` and `tower` in `Cargo.toml`, plus a `Router::new()` chain in `main.rs` or a `router.rs` module. Almost always paired with Tokio. The dominant 2026 choice for new HTTP services.
- **Actix-web**: `actix-web` in `Cargo.toml`, plus `HttpServer::new(|| App::new()...)` in the entry point. Mature, performant, slightly heavier learning curve than Axum. Common in projects that started before 2022.
- **Rocket**: `rocket` in `Cargo.toml`, plus `#[launch]` or `#[rocket::main]` attribute. Rocket 0.5 (2023) is the modern release line; anything still on 0.4 is on the unmaintained pre-Tokio branch and is a finding.
- **Warp**: `warp` plus a `warp::path!(...)` filter chain. Less common in 2026; new work usually moves to Axum.
- **Tide**: `tide` and `async-std`. Effectively legacy in 2026; presence is a finding paired with the async-std finding above.
- **Leptos**: `leptos` plus `#[component]` and the `view!` macro in JSX-shaped trees. Full-stack with server functions; modern choice for Rust frontends. Almost always paired with `axum` or `actix-web` for the server side.
- **Dioxus**: `dioxus` plus `rsx!` macros. Cross-platform (web, desktop, mobile, TUI); the audit notes the target list.
- **Tauri**: `tauri` in `Cargo.toml` plus a `tauri.conf.json` at the repo root. Desktop app; the audit covers both the Rust backend and the (usually) JavaScript frontend.

Frameworks not in this list emit an INFO note in the architecture artifact ("framework not in canonical signature set"); the hireability tier still drives the headline finding per [04-stack.md](../../methodology/04-stack.md). Rust itself sits in the moderate tier in the 2026 rubric.

## License cascade and the dual-license norm

The strong Rust convention is dual-licensing under MIT OR Apache-2.0. This is the license posture of the Rust standard library, of nearly every crate in the top-100 downloads on crates.io, and of the Rust toolchain itself. A project that ships under MIT OR Apache-2.0 inherits a clean upstream; a project that ships under a more restrictive license is making a deliberate choice the packet should name.

The pull-list `cargo deny check licenses` enforces is straightforward in the dual-license case: any MIT, Apache-2.0, MIT OR Apache-2.0, BSD-3-Clause, ISC, Unicode-DFS-2016, MPL-2.0, and similar permissive licenses are clean. Findings fire on:

- **GPL or AGPL crates in the transitive tree**. These force the application to inherit copyleft. The packet names the crate, the parent dep that requires it, the GPL/AGPL version, and the remediation path (usually a different crate that does the same thing under a permissive license, or vendoring a stripped-down equivalent).
- **Unlicensed or missing-license crates**. A `Cargo.toml` with no `license` field is a defect upstream; the audit cannot assert clean license posture for the project until those crates are resolved. The packet names them.
- **Non-OSI licenses on the project itself**. Custom licenses, "source-available" terms, or BSL-style time-locked relicensing are findings if the seller has not surfaced them proactively in the data room.
- **License-incompatibility cascades**. An MPL-2.0 crate inside an Apache-2.0-only project is technically compatible (MPL allows it) but the audit calls it out so the buyer's counsel sees the dependency clearly.

A clean Rust packet ships the output of `cargo about generate` as an attribution-list appendix artifact. License posture is named in the architecture narrative, not summarized only.

## Typical false positives

- `cargo audit` flags advisories against crates the project pulls in only as a dev-dependency (`[dev-dependencies]` block) or only for a non-default feature flag. A clean packet names the crate, names the dependency kind (build, dev, target-specific, feature-gated), and explains why the production runtime does not pull the vulnerable code path. Suppress in the packet only with a written rationale.
- `cargo geiger` reports unsafe usage in the standard library when scanning with `--all-features`; std unsafe is audited by the Rust project itself and is not actionable. Suppress with `--exclude std` or read past it.
- `cargo deny check duplicates` fires whenever two transitive deps pull different major versions of the same crate (the common case: `rand` 0.8 and `rand` 0.9 coexisting). Most duplicates are benign and resolve with the next `cargo update`; the finding fires only when the duplicates are pinned by the project's own constraints or have meaningful binary-size impact.
- `clippy::pedantic` and `clippy::nursery` together produce thousands of warnings on any codebase that has not opted into them; ship only `clippy::all` plus the project's own `clippy.toml` allowlist for the security signal. Pedantic findings go in the architecture writeup, not the security findings list.
- `cargo tarpaulin` cannot instrument async test code on all targets; an "untested" report on a Tokio-based codebase may reflect a tarpaulin limitation, not missing tests. Cross-check with `cargo llvm-cov` on macOS or ARM targets before promoting the finding.
- `gitleaks` flags Rust-style hex constants in `tests/fixtures/` and `examples/` directories that look like API keys or signing material. Mark `is_sensitive: false` with a note pointing at the fixture path; the convention in Rust is to keep test material in `tests/` rather than a separate fixtures folder, so the location alone is the disambiguator.
- The RustSec Advisory Database lags upstream CVE feeds by days to weeks for less popular crates. Cross-checking against `osv-scanner` is what keeps a Rust packet from missing a known issue that had not yet been merged into the Rust-only database.
- `cargo deny` fires `unmaintained` warnings on crates whose latest release is more than 12 months old. Many of those crates are simply done (the API is stable, the surface is small, no maintenance is needed). Read the upstream repo before promoting; a finding fires when the crate has open security issues or has been explicitly deprecated by the author.

## Minimum acceptable depth

* All eight tools above run cleanly with no skipped checks on the most recent commit. If the project pins a Rust toolchain that `cargo audit` or `cargo deny` no longer support, the packet names the pinned version, the date of pinning, and the upgrade work required before the scanners run.
* `cargo audit` runs against the live RustSec database (not a vendored snapshot); the packet notes the database fetch timestamp. `cargo deny check` runs with the project's own `deny.toml` if present; if absent, the packet runs `cargo deny init` and ships the generated `deny.toml` as a recommended remediation artifact.
* `cargo geiger` runs with `--all-features` and the output is included as an appendix artifact. The project's own unsafe-line count plus the top-three transitive offenders are quoted in the security writeup, with every project-owned `unsafe` block labeled FFI / performance / unjustified per the unsafe-audit-posture section above.
* Test coverage measured, not assumed: actual percentage from `cargo tarpaulin`, `cargo llvm-cov`, or `grcov`, not a test-file-count heuristic. Async-heavy codebases get the coverage figure plus a one-line note on which runner produced it and whether async paths were instrumented.
* The third-party vendor inventory cross-references all crates declared in `Cargo.lock` (not just `Cargo.toml`, which omits transitive resolution) against the vendor signature table. Workspace projects pull from every member crate's effective dependency set, not just the root manifest. Any vendor not in the table gets a manual lookup before the packet ships. Crates with no published license metadata in their `Cargo.toml` get flagged separately and resolved by reading the upstream repo.
* Credential exposure check includes a deliberate pass over `.env` files, `.env.example` files, any `secrets.toml` or `production.toml` from `config-rs` projects, hardcoded constants in `src/`, `tests/`, and `examples/`, and the git history for any of the above. A single historical commit of a real secret is a finding even if the current `HEAD` is clean.
* License posture names the application license (project's own `LICENSE` file and the `license` field in `Cargo.toml`), the dual-license norm comparison, the gem-equivalent transitive license inventory from `cargo about`, and any GPL or AGPL cascade that would force the application to inherit a copyleft obligation. The `cargo about` output is included as an appendix artifact, not summarized only.
* Architecture findings cite specific file and line locations. For Axum or Actix projects: the router definition file, the middleware stack, the error-handling type, and any handler over 100 lines. For Leptos or Dioxus projects: the component tree entry point, the server-function module, and the hydration boundary. For workspace projects: the member-crate graph and any member crate that is imported by more than three other members (a centralization smell). Abstract diagrams without `file:line` citations do not ship.
* Stack hireability writeup names the Rust toolchain version, the edition spread across workspace members, the async runtime, the framework, and an honest 2026 read on the hiring market. Rust hiring sits in the moderate tier per [04-stack.md](../../methodology/04-stack.md); supply is real but skews senior, and replacement cost is higher than Python or TypeScript. The packet quotes the rubric and adds the project-specific reality.
* Key-person risk callouts surface the patterns specific to Rust codebases: heavy use of macro_rules! or proc-macro crates authored in-repo (these are read-only DSLs that lock future maintainers out unless documented), trait hierarchies more than three levels deep with associated-type bounds that constrain implementers, custom derive macros under `proc_macros/` member crates, and any module that abuses the type system in service of compile-time invariants the original author understood implicitly. These are the patterns that make a Rust codebase elegant to its original author and opaque to a new senior hire.

### What deterministic tools cover, and what they do not

Deterministic Rust tools (`cargo audit`, `cargo deny`, `cargo geiger`, `cargo tarpaulin`, `cargo llvm-cov`, `cargo about`, `semgrep`) cover the SCA, license, coverage, and unsafe-count zones cleanly. They are fast, reproducible, and citation-grade.

What they do not cover well, and what an AI specialist pass adds: reading each project-owned `unsafe` block in context to label it FFI / performance / unjustified, distinguishing a sound macro_rules! pattern (Tokio's own `select!`) from a single-author DSL that locks future maintainers out, recognizing async runtime tuning that signals real load-testing experience versus default-configuration cargo-cult code, evaluating whether a trait hierarchy is reaching for legitimate compile-time guarantees or for cleverness, and reading framework-shaped projects (Axum router compositions, Leptos hydration boundaries) end-to-end for the architectural drift that happens when a Rust service has been refactored across two or three major framework versions. Those are the findings that a Closeread-grade Rust packet adds on top of the deterministic baseline.
