# Elixir appendix

Tools an auditor reaches for when the primary stack is Elixir, the typical false positives to suppress, and the minimum acceptable depth of coverage for a Closeread-grade packet on an Elixir codebase.

"Elixir" in audit terms covers Phoenix (the dominant case in acquisition-side diligence, usually with LiveView on the frontend), the Nerves embedded toolchain, the Broadway and Oban data-pipeline ecosystems, and the long tail of plain-Mix library projects published to Hex.pm. The runtime is Erlang/OTP, and the audit posture must address both the Elixir code under inspection and the OTP version it depends on. Dependencies are managed by Mix with a committed `mix.lock`. The toolchain below covers all of these layers.

## Tools

| Zone | Tool | Notes |
|---|---|---|
| SCA | `mix deps.audit`, `mix hex.audit`, `osv-scanner` | `mix deps.audit` (provided by the `dep_audit` Hex package) reads `mix.lock` against the Sobelow advisory database. `mix hex.audit` is built into Mix itself and reports retired packages. `osv-scanner` adds the OSV breadth that the Elixir-only feeds miss. Run all three. |
| Credentials | `gitleaks`, `trufflehog` | Same as Node and Ruby. Watch for `config/runtime.exs` files that interpolate secrets via `System.fetch_env!/1` correctly but also keep a `config/dev.secret.exs` or `config/prod.secret.exs` with literals from earlier in the project's history. |
| Third party | manifest review + source grep | Parse `mix.exs` and `mix.lock` against the vendor signature table. The lock file is authoritative for transitive resolution and pins the exact Hex package version plus checksum. |
| Test coverage | `ExCoveralls`, `mix test --cover` | `mix test --cover` uses the built-in `:cover` tool from OTP; ExCoveralls wraps it with HTML and JSON reporters and integrates with most CI providers. Check `mix.exs` for `test_coverage: [tool: ExCoveralls]` and the `coveralls.json` config file. |
| Security | `mix sobelow`, `semgrep --config=auto` | Sobelow is the Phoenix-specific SAST and is non-negotiable when a `lib/*_web/` directory is present. Semgrep covers non-Phoenix Elixir and adds polyglot patterns Sobelow does not run. |
| License | `mix licenses`, manual `mix.lock` review | License metadata lives in each package's `mix.exs` under the `:licenses` key. The `licenses` Hex package pulls a flat report; cross-reference against the project's stated license tier, and flag any AGPL cascade that the author may not realize they inherited. |
| Architecture | `mix xref`, `mix app.tree`, manual `use`/`import`/`alias` grep | `mix xref graph` produces a module-level dependency graph. `mix app.tree` shows the OTP application supervision boundaries. For Phoenix projects, the contexts in `lib/` are the architecturally meaningful unit; the `*_web/` boundary is the second. |

## Typical false positives

* `mix deps.audit` flags advisories against packages the application only loads in the `:dev` or `:test` Mix environments. A clean packet names the package, names the env, and explains why the production runtime does not pull the vulnerable code path. Suppress in the packet only with a written rationale.
* Sobelow flags `Plug.Conn.get_req_header/2` and other request-parameter access as injection risk even when the controller pattern-matches on a known atom set one layer up or when `Phoenix.Controller.action_fallback/1` is in force. Read the controller and the router pipeline end-to-end before promoting the finding.
* Sobelow's `XSS.Raw` check fires on every `raw/1` call in a LiveView template even when the input is a server-side enum constant. Confirm whether the value originates from user input or from a hardcoded module attribute before treating it as exploitable.
* Sobelow's `Config.HTTPS` finding can fire on releases that terminate TLS at a load balancer (Fly.io, Gigalixir, AWS ALB) where the Phoenix endpoint itself does not need to bind to 443. The packet should name the deployment topology before promoting.
* ExCoveralls can report 100% on a project that has no real test surface if the `:skip_files` regex over-matches or if `Application.put_env(:phoenix, :serve_endpoints, false)` is left on for tests that never boot the supervision tree. Verify the source scope and the actual `cover/excoveralls.json` line counts before trusting the headline number.
* `gitleaks` flags Phoenix `:secret_key_base` values in `config/dev.exs` when those values are placeholders or are themselves derived from `System.get_env/1`. Read the surrounding Elixir before promoting; a genuine leak is usually a 64-byte base64 string committed as a literal, not an interpolation.
* Test fixtures in `test/support/fixtures/` and Bypass/Mox-based HTTP recordings routinely contain example API keys and bearer tokens that look real to credential scanners. Mark `is_sensitive: false` with a note pointing at the fixture path.
* The Sobelow advisory feed lags upstream CVE feeds by days to weeks for less popular Hex packages. Cross-checking against `osv-scanner` is what keeps an Elixir packet from missing a known issue that had not yet been merged into the Elixir-only database. `mix hex.audit` is a separate concern; it surfaces packages the maintainer has retired, which is a supply-chain signal but not always a vulnerability signal.

## Secrets, config, and the runtime.exs pattern

Modern Phoenix (1.6+) ships secrets through `config/runtime.exs`, which is evaluated when the release boots, not at compile time. The expected pattern is:

```elixir
# config/runtime.exs
if config_env() == :prod do
  secret_key_base = System.fetch_env!("SECRET_KEY_BASE")
  database_url = System.fetch_env!("DATABASE_URL")

  config :my_app, MyAppWeb.Endpoint,
    secret_key_base: secret_key_base

  config :my_app, MyApp.Repo,
    url: database_url
end
```

A clean packet verifies that:

1. No production secrets live in `config/prod.exs` (which IS compiled into the release).
2. `config/runtime.exs` exists and uses `System.fetch_env!/1` (which raises on missing env) rather than `System.get_env/1` (which returns nil and propagates a runtime error later).
3. The deployment platform (Fly.io, Gigalixir, AWS, Render) injects the env vars at boot, not at build.
4. `.env` files, when present, use `dotenv` (the older `dotenv` Hex package), `dotenvy_elixir`, or `dotenv_parser`. The `Application.put_env/3` call that loads them sits in `config/runtime.exs` or in a dev-only `lib/my_app/dev.ex`, not in `config/dev.exs` (which is again compile-time).
5. `config/*.secret.exs` files, a pattern from older Phoenix versions, are in `.gitignore` and have no historical commits in `git log --all -- config/*.secret.exs`.

The single most common Elixir credential finding in 2026 acquisition diligence is a pre-1.6 Phoenix application that has not migrated from `config/prod.secret.exs` to `runtime.exs`. Secrets sit in a file that is gitignored at HEAD but were committed once in 2021 and never rotated. The fix is a one-day migration; the finding is a P1.

## Runtime version posture

Elixir runs on the Erlang/OTP virtual machine. The audit must name BOTH versions and check both against their support windows.

* **Erlang/OTP 25** reached end of support in **December 2025**. Any project still on OTP 25 in 2026 is on a runtime with no security patches. P1 finding.
* **Erlang/OTP 26** is supported through approximately mid-2027. Acceptable.
* **Erlang/OTP 27** is the current release line and is the right target for new audits.
* **Elixir 1.14** dropped support for OTP 24 and below; **Elixir 1.15** dropped OTP 23. **Elixir 1.16** is the current stable line in 2026, with **Elixir 1.17** in beta carrying the new type-system work.

The version pair lives in two places that must agree: `mix.exs` declares `:elixir` (and sometimes `:erlang`) version constraints, and the deployment artifact (a Dockerfile, an `.tool-versions` file for asdf or mise, an `elixir_buildpack.config` for older Heroku-style platforms) declares the actual installed runtime. A common drift pattern is `mix.exs` allowing `~> 1.15` while the Dockerfile pins `elixir:1.14.5-otp-25`; the packet names both.

## Phoenix LiveView detection and audit posture

LiveView changes the audit surface meaningfully. Detection is straightforward:

```bash
grep -rn "use Phoenix.LiveView" lib/
grep -rn "live_render" lib/
grep -rn "phx-click\|phx-submit\|phx-change" lib/
ls assets/js/app.js  # check for `let liveSocket = new LiveSocket(...)`
```

A LiveView codebase gets three extra audit checks on top of the standard Phoenix posture:

1. **Authorization at the mount boundary.** Every `def mount(_params, _session, socket)` callback should call an `on_mount/4` hook or an explicit auth check. A LiveView that reads `current_user` from the socket assigns but never verifies the assign was set is exploitable in the same way a controller without `Plug.EnsureAuthenticated` is.
2. **Event handler trust.** Every `def handle_event("save", params, socket)` callback receives user-controlled `params`. The pattern-match on the event name is not a security boundary; the validation inside is.
3. **PubSub fan-out scoping.** `Phoenix.PubSub.subscribe(MyApp.PubSub, topic)` with a user-controlled `topic` string is a tenancy violation if topics are not namespaced. A clean packet checks that subscribe calls scope the topic to `"user:#{user.id}"` or equivalent and not to a raw `params["channel"]`.

Sobelow does not catch any of these by default. They are AI-specialist findings.

## Minimum acceptable depth

* All seven tools above run cleanly with no skipped checks on the most recent commit. If the project pins an older Elixir or OTP that `sobelow` or `mix deps.audit` no longer support, the packet names the Elixir version, the OTP version, the EOL date for each (Elixir 1.14 EOL December 2024, Elixir 1.15 EOL approximately mid-2026, Elixir 1.16 current; OTP 25 EOL December 2025, OTP 26 supported, OTP 27 current), and the upgrade work required before the scanners run.
* Sobelow runs with default confidence and the full check set; results capped at 8 high, 12 medium, 6 low in the packet to avoid finding-flood. Any suppressed check is named with a one-line rationale. Phoenix LiveView projects also get the three LiveView-specific manual checks above documented inline.
* Test coverage measured, not assumed: actual percentage from `mix coveralls` or `mix test --cover`, not a test-file-count heuristic. The Phoenix `mix test` task with `:async` enabled is the default and is acceptable, but the packet notes whether `async: false` is in force for any test module that touches the database without `Ecto.Adapters.SQL.Sandbox`, because that pattern silently serializes the suite.
* The third-party vendor inventory cross-references all Hex packages declared in `mix.lock` (not just `mix.exs`, which omits transitive resolution) against the vendor signature table. Any vendor not in the table gets a manual lookup before the packet ships. Packages with no published license in their `mix.exs` `:licenses` field get flagged separately and resolved by reading the upstream repo.
* Credential exposure check includes a deliberate pass over `config/runtime.exs`, `config/prod.exs`, `config/dev.exs`, any `config/*.secret.exs` files, any `.env*` files, and the Dockerfile or release config. The `runtime.exs` migration is verified as described above. A single historical commit of a `*.secret.exs` file with literal secrets is a finding even if the current `HEAD` is clean.
* License posture for Phoenix projects names the application license and the Hex package licenses pulled in transitively. Hex.pm overwhelmingly carries MIT (the default for `mix new`), with Apache 2.0 a close second for ecosystem libraries that originated at companies (Broadway, Telemetry, Erlang/OTP itself is Apache 2.0). AGPL is rare on Hex but appears (the `livebook` open-source variant is AGPL; some Oban Pro plugins were AGPL before going proprietary). Any AGPL gem that would force the application to inherit a copyleft obligation is a P1 finding for an acquisition target.
* Architecture findings cite specific file and line locations. For Phoenix: `lib/my_app/` for contexts, `lib/my_app_web/` for the web boundary, `lib/my_app/application.ex` for the top-level supervision tree, and any module that exceeds 400 lines (the unofficial threshold where a Phoenix context typically should be split). For Nerves: the `mix.exs` `:target` configuration and the firmware build pipeline. Abstract diagrams without `file:line` citations do not ship.
* Stack hireability writeup names the Elixir version, the Phoenix version (Phoenix 1.7 is the current release line in 2026 with LiveView 1.0; Phoenix 1.6 is the last LiveView 0.x line), and an honest 2026 read on the hiring market. Elixir and Phoenix hiring is narrow-tier, narrower than Ruby and significantly narrower than Node or Python. Per-candidate depth is high; senior Elixir engineers are typically polyglots with strong functional or distributed-systems backgrounds. Concentrated geographically in firms that already run Elixir at scale (Discord, Pinterest, Bleacher Report, the Nerves embedded community). An acquirer should expect to either inherit the existing team or commit to a one-to-two-quarter knowledge-transfer window.

## Key-person risk specific to Elixir and OTP

Elixir codebases concentrate key-person risk in a different shape than Ruby or Python codebases do. The patterns to surface in the packet:

* **Custom GenServer hierarchies.** A `lib/my_app/cache/`, `lib/my_app/scheduler/`, or `lib/my_app/worker/` directory with multiple GenServers that hand-roll patterns the ecosystem now ships (Cachex, Quantum, Oban) usually traces to one author who built the system before the canonical libraries existed. The replacement cost is moderate but the institutional knowledge is concentrated.
* **Custom Supervisor strategies.** Most Phoenix applications use the default `:one_for_one` strategy on a flat supervisor at the top level. A codebase with deep nested supervisors using `:rest_for_one`, `:one_for_all`, or a custom `:max_restarts` window almost always reflects a deliberate fault-tolerance design that the original author understood and that is not documented for anyone else.
* **Hand-rolled distributed coordination.** Calls to `:global.register_name/2`, `:pg.join/2`, `Node.connect/1`, or libcluster strategies beyond the default `Cluster.Strategy.Epmd` are deep OTP territory. The author who wrote them understands BEAM clustering; the new senior hire might not. A clean packet names every such pattern with `file:line` and assesses whether the same outcome could be achieved with a simpler dependency (Phoenix.PubSub for messaging, Horde for distributed registries).
* **Macro-heavy DSLs.** Any module under `lib/my_app/` that defines a `defmacro` or uses `__using__/1` to inject behavior into callers is metaprogramming. Phoenix's own routers, Ecto's own schemas, and Plug's own builders all do this and are well-documented in the community. A project-internal DSL that does this without README documentation is a key-person liability of the same shape as a Ruby `method_missing` chain or a Python metaclass.
* **NIFs and Ports.** `:erlang.load_nif/2` calls or modules that wrap a C library through a Port are runtime extensions that crash the BEAM if they fault. The packet names the language of the underlying native code, the maintainer, and the licensing posture of the foreign library.

These are the patterns that make an Elixir codebase readable to its original author and opaque to a new senior hire. They are also the patterns that AI specialists handle better than deterministic scanners.

### What deterministic tools cover, and what they do not

Deterministic Elixir tools (`mix deps.audit`, `mix hex.audit`, `sobelow`, `semgrep`, `ExCoveralls`, `mix xref`) cover the SCA, credential, SAST, coverage, and dependency-graph zones cleanly. They are fast, reproducible, and citation-grade.

What they do not cover well, and what an AI specialist pass adds: reading the supervision tree to understand the project's failure model, recognizing whether a GenServer's `handle_call/3` callbacks are bottlenecking the system, distinguishing a sound metaprogramming pattern (Ecto's `schema do ... end`) from a single-author DSL that locks future maintainers out, surfacing PubSub topic-namespacing gaps in LiveView code, and assessing whether the runtime version posture (Elixir + OTP pair) is on a supported track. Those are the findings that a Closeread-grade Elixir packet adds on top of the deterministic baseline.
