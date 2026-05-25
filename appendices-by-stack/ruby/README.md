# Ruby appendix

Tools an auditor reaches for when the primary stack is Ruby, the typical false positives to suppress, and the minimum acceptable depth of coverage for a Closeread-grade packet on a Ruby codebase.

"Ruby" in audit terms covers Rails (overwhelmingly the dominant case in acquisition-side diligence), Sinatra (modular and classic), Hanami, and the long tail of plain-Ruby command-line and library projects. The runtime is almost always managed by `rbenv`, `asdf`, `mise`, or `chruby`, and dependencies almost always by Bundler with a committed `Gemfile.lock`. The audit posture changes meaningfully across these layers, but the toolchain below covers all of them.

## Tools

| Zone | Tool | Notes |
|---|---|---|
| SCA | `bundler-audit`, `osv-scanner` | `bundler-audit` reads `Gemfile.lock` against `ruby-advisory-db`; `osv-scanner` adds the OSV breadth that the Ruby-only DB misses. Run both. |
| Credentials | `gitleaks`, `trufflehog` | Same as Node and Python. Watch for `config/credentials.yml.enc` paired with a committed `config/master.key`, and for `.env` files that shipped before `dotenv-rails` was added to `.gitignore`. |
| Third party | manifest review + source grep | Parse `Gemfile`, `Gemfile.lock`, and any `*.gemspec` against the vendor signature table. The lock file is authoritative for transitive resolution. |
| Test coverage | `simplecov`, `rspec`, `minitest` | SimpleCov instruments either RSpec or Minitest runs; the project's `spec/spec_helper.rb` or `test/test_helper.rb` shows which. Check for `coverage/.last_run.json` for the actual line percentage. |
| Security | `brakeman`, `semgrep --config=auto` | Brakeman is the Rails-specific SAST and is non-negotiable when a `config/application.rb` is present. Semgrep covers non-Rails Ruby and adds polyglot patterns Brakeman does not run. |
| License | `bundler-license-report`, `license_finder` | License metadata lives in each gem's `gemspec`. Pull the report, cross-reference against the project's stated license tier, and flag any GPL or AGPL cascade that the author may not realize they inherited. |
| Architecture | `rails stats`, manual `require`/`include`/`extend` grep | `rails stats` gives the controller and model line counts plus the test-to-code ratio. For non-Rails projects, an `ast`-driven import graph or a `ripper`-based pass surfaces the in-repo dependency edges. |

## Typical false positives

* `bundler-audit` flags advisories against gems that the application only loads in `:development` or `:test` Bundler groups. A clean packet names the gem, names the group, and explains why the production runtime does not pull the vulnerable code path. Suppress in the packet only with a written rationale.
* Brakeman flags `params[:id]` and other unsanitized parameter access as SQL injection or mass assignment risk even when the controller calls `find` (which casts to integer) or when strong parameters are in force one layer up. Read the controller end-to-end before promoting the finding.
* Brakeman's "unsafe redirect" check (`CheckRedirect`) fires on any `redirect_to params[...]` even when the project has registered a custom URL whitelister. Confirm whether a `before_action` filters the param before treating it as exploitable.
* SimpleCov can report 100% on a project that has no real test surface if `add_filter` and `track_files` are mis-scoped, or if the runner exits before the `at_exit` hook flushes. Verify the source scope and the actual `coverage/.resultset.json` line counts before trusting the headline number.
* `gitleaks` flags Rails `secret_key_base` values in `config/secrets.yml` when those values are placeholders or are themselves derived from `ENV[...]`. Read the surrounding YAML before promoting; a genuine leak is usually a 128-character hex string committed as a literal, not an interpolation.
* Test fixtures in `spec/fixtures/`, `test/fixtures/`, and VCR cassettes under `spec/vcr_cassettes/` routinely contain example API keys and bearer tokens that look real to credential scanners. Mark `is_sensitive: false` with a note pointing at the fixture path.
* `ruby-advisory-db` lags upstream CVE feeds by days to weeks for less popular gems. Cross-checking against `osv-scanner` is what keeps a Ruby packet from missing a known issue that had not yet been merged into the Ruby-only database.

## Minimum acceptable depth

* All seven tools above run cleanly with no skipped checks on the most recent commit. If the project pins an older Ruby that `brakeman` or `bundler-audit` no longer support, the packet names the Ruby version, the EOL date (Ruby 3.0 EOL March 2024, Ruby 3.1 EOL March 2025, Ruby 3.2 EOL March 2026, Ruby 3.3 current), and the upgrade work required before the scanners run.
* Brakeman runs with default confidence (`-w 1`) and full check set; results capped at 8 high, 12 medium, 6 low in the packet to avoid finding-flood. Any suppressed check is named with a one-line rationale.
* Test coverage measured, not assumed: actual percentage from `simplecov` (or `rspec --format documentation` plus the coverage artifact), not a spec-file-count heuristic. Rails projects with `rails stats` get the test-to-code ratio quoted alongside the SimpleCov number, because the two answer different questions.
* The third-party vendor inventory cross-references all gems declared in `Gemfile.lock` (not just `Gemfile`, which omits transitive resolution) against the vendor signature table. Any vendor not in the table gets a manual lookup before the packet ships. Gems with no published license metadata in their `gemspec` get flagged separately and resolved by reading the upstream repo.
* Credential exposure check includes a deliberate pass over `config/credentials.yml.enc` plus `config/master.key`, `config/secrets.yml`, `config/database.yml`, and any `.env*` files in repository history. The encrypted-credentials pattern is safe only when `master.key` is in `.gitignore` and never committed; a single historical commit of `master.key` is a finding even if the current `HEAD` is clean.
* License posture for Rails projects names the application license, the gem licenses pulled in transitively, and any GPL or AGPL gem that would force the application to inherit a copyleft obligation. The output of `bundler-license-report` is included as an appendix artifact, not summarized only.
* Architecture findings cite specific file and line locations. For Rails: `app/controllers/`, `app/models/`, `app/services/` (or `app/operations/`, `app/interactors/`, whichever service-object convention the project uses), and any `app/concerns/` that exceeds 200 lines (a common monolith decomposition smell). For Sinatra: the modular-vs-classic split and the `Sinatra::Base` subclass surface. Abstract diagrams without `file:line` citations do not ship.
* Stack hireability writeup names the Ruby version, the Rails major version (Rails 8 is the current release line in 2026; Rails 7.1 is the most recently supported LTS), and an honest 2026 read on the hiring market. Ruby and Rails hiring is moderate-tier, narrower than Node or Python but deeper per-candidate, and concentrated in firms that already run Rails at scale. The audited example in this repo (`chatwoot-audit-2026-05-22.md`) is a Rails codebase at 177,915 lines of Ruby; its packet uses this template.
* Key-person risk callouts surface the patterns specific to Ruby codebases: heavy metaprogramming concentrated in one author's commit history (DSL definitions, `method_missing` chains, `define_method` factories), custom DSL adoption that lacks public documentation, and any `lib/` directory that monkey-patches a vendored gem or core Ruby class. These are the patterns that make a Rails codebase readable to its original author and opaque to a new senior hire; they are also the patterns that AI specialists handle better than deterministic scanners.

### What deterministic tools cover, and what they do not

Deterministic Ruby tools (`bundler-audit`, `brakeman`, `semgrep`, `simplecov`, `bundler-license-report`) cover the SCA, credential, SAST, coverage, and license zones cleanly. They are fast, reproducible, and citation-grade.

What they do not cover well, and what an AI specialist pass adds: reading Rails concerns to detect whether they share state across unrelated controllers, recognizing service-object naming conventions that are not enforced by the framework, distinguishing a sound metaprogramming pattern (Rails' own `ActiveRecord::Base.has_many`) from a single-author DSL that locks future maintainers out, and surfacing the architectural drift that happens when a Rails monolith has been decomposed into `app/services/` over several years by different hands. Those are the findings that a Closeread-grade Ruby packet adds on top of the deterministic baseline.
