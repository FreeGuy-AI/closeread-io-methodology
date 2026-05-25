# Closeread CLI Ergonomics Audit v1

> **CORRECTION banked 2026-05-24 Day 10 ~11:30pm:** This audit's claim of a `--stack` double-shift bug in `audit-bootstrap.sh` is **WRONG**. Empirical testing (`--stack node`, `--stack=node`, `--install --stack node`, `--stack node --install`) returns `STACK=node` correctly in all four cases. The `for arg in "$@"` loop captures the original arg list at iteration start, so the explicit shift inside the `--stack)` case branch and the unconditional bottom shift do not interact destructively. The sub-agent that wrote this audit confidently reported "Confirmed bug... real ship-now fix" with full pseudo-evidence. I almost shipped a fix for a non-bug. **Lesson 026 candidate (banking separately):** sub-agents can hallucinate bugs with confident framing. The mitigation is empirical: every claimed bug must be reproduced by a 30-second test script before any "fix" PR is opened. All OTHER recommendations in this audit are unverified — treat as hypotheses requiring empirical confirmation before any implementation work.

Status: DRAFT, Day 10 (2026-05-24). Companion to `README.md` in this directory. Target: an external contributor can open a PR implementing 6+ of the changes below without further consultation.

The surface in scope is what a new founder hits in the first 10 minutes: `audit-bootstrap.sh` (the toolchain pre-flight), the eventual `closeread` CLI (implied by the audit-packet templates, not yet implemented), and the two MCP servers scaffolded at `mcp-server/` and `verify-mcp/`. The reference CLI itself ships Day 180 per `README.md`; this audit captures what to fix BEFORE that ship so the first PR-able surface is bootstrap and the MCPs.

The lens: every friction point is a person on Hacker News at 11pm with 90 seconds of patience. If the second command they type returns a confusing error, the project loses them. The pattern across all 8 changes below is the same: replace inferred behavior with named flags, replace silent fallbacks with explicit defaults, and add a dry-run path everywhere a destructive or non-idempotent action lives.

---

## Top 8 changes

### 1. Rename `--install` to `--install-missing` and add `--dry-run`

The current `audit-bootstrap.sh` flag is ambiguous. A reader sees `--install` and reasonably wonders "install what? everything? overwrite my existing tools?" The script actually only installs missing tools, leaving present ones alone, but the flag does not say so. A new user has to read the source to confirm idempotency.

Worse: there is no way to PREVIEW what the script will do. `audit-bootstrap.sh --install` either runs the installs or you read the source. A new contributor on a corporate Mac with locked-down brew permissions will run it, hit a brew install failure halfway through, and lose trust in the tool.

**Before:**
```bash
./bin/audit-bootstrap.sh --install
# silently runs brew install for every missing tool, no preview, no per-tool confirm
```

**After:**
```bash
./bin/audit-bootstrap.sh --dry-run
# prints: "would install: gitleaks, osv-scanner, pip-audit"
# exit code 0 (success, nothing changed)

./bin/audit-bootstrap.sh --install-missing
# installs only tools not present; prints "skipping: jq (already installed)"

./bin/audit-bootstrap.sh --install-missing --yes
# skips per-package confirm prompts (for CI)
```

The pair of `--dry-run` and `--install-missing --yes` gives a new contributor both the safety to look and the speed to ship.

### 2. Fix the `--stack` flag double-shift bug and add tab-completion

The current loop in `audit-bootstrap.sh`:

```bash
for arg in "$@"; do
  case $arg in
    --stack=*) STACK="${arg#*=}" ;;
    --stack) shift; STACK="$1" ;;
  esac
  shift 2>/dev/null || true
done
```

The unconditional `shift 2>/dev/null || true` at the bottom of the loop fires AFTER the explicit `shift; STACK="$1"` inside `--stack)`, meaning `./bin/audit-bootstrap.sh --stack node` shifts twice and silently sets `STACK="all"` again on certain bash invocations. The `--stack=node` form works because it parses without shifting. New users hit this on the form that looks more natural to type.

Symptom for the new user: `--stack node` appears to run, prints "Universal" + "Appendix A: Node" but ALSO runs Python, PHP, Ruby, Go scans. They conclude the flag is broken and stop using it.

**Before (current loop):**
```bash
./bin/audit-bootstrap.sh --stack node
# silently runs all stacks anyway
```

**After:**
```bash
./bin/audit-bootstrap.sh --stack node
# runs only node stack, prints "stack: node (use --stack=all to scan everything)"

./bin/audit-bootstrap.sh --stack=node     # equivalent
./bin/audit-bootstrap.sh --stack auto     # detects from lockfiles in $PWD
```

Add a `--stack auto` mode that reads the repo's lockfiles (`package-lock.json`, `requirements.txt`, `Gemfile.lock`, etc.) and picks the matching appendix. This is the sensible default for a founder running the script in their own repo: they should not have to tell the tool what stack their own code is in.

While at it, ship `_audit-bootstrap` completion to `completions/bash/` and `completions/zsh/` so `./bin/audit-bootstrap.sh --st[TAB]` expands to `--stack`. Five lines of shell, removes a class of typos.

### 3. Replace the unicode-only status output with a `--format` flag

Current output uses unicode glyphs `✓` and `✗`. On terminals without UTF-8 (corporate Windows-via-WSL setups, some CI runners, anyone with a misconfigured locale) these render as `?` boxes or get stripped. The script also prints all output unconditionally, so piping to a file gives a colorful but unparseable mess.

**Before:**
```bash
./bin/audit-bootstrap.sh
# === Universal (required for all stacks) ===
#   ✓ gitleaks (credential scanner)
#   ✗ osv-scanner (OSV.dev CVE scanner)
#     install: brew install osv-scanner
```

**After:**
```bash
./bin/audit-bootstrap.sh --format pretty   # default; colored unicode for humans
./bin/audit-bootstrap.sh --format ascii    # [OK] / [MISSING], no color, no unicode
./bin/audit-bootstrap.sh --format json     # machine-readable, scripts can consume

# json shape:
# {"tool": "osv-scanner", "status": "missing", "install_cmd": "brew install osv-scanner", "stack": "node", "required": true}
```

The JSON mode unlocks the bigger story: a wrapper like `closeread doctor` can call `audit-bootstrap.sh --format json --stack auto`, parse the output, and decide whether to proceed with the audit or auto-install missing required tools. Today that wrapper has to scrape unicode.

### 4. Ship `closeread audit <repo>` as the top-level entry point with `--out`, `--stack`, `--tiers`

The `README.md` in this directory describes the intended user experience: a founder runs the CLI against their own repo and gets a packet. The audit-packet templates imply the inputs (repo path, stack, tier access level, customer name) but no single `closeread audit` command exists yet. Currently a user has to read both the template and the appendices, manually run each scanner from each appendix, manually populate the template, and manually compose the packet. This is the single largest piece of missing ergonomics.

**Before (today):**
```bash
# user reads template-v2.md
# user reads appendix A for Node
# user runs: npm audit --json > /tmp/scratchpad/npm-audit.json
# user runs: osv-scanner --lockfile=package-lock.json --format json > /tmp/scratchpad/osv.json
# user reads gitleaks docs, runs: gitleaks detect --source=. --report-path=/tmp/scratchpad/gitleaks.json
# user runs: rg 'process\.env\.\w+\s*\|\|\s*""' --type ts
# user copy-pastes outputs into a markdown packet
# 4 hours later: a partial packet
```

**After:**
```bash
closeread audit ./my-repo
# auto-detects stack, runs all required scanners for that stack,
# writes packet to ./closeread-packet-{date}-{customer}.md

closeread audit ./my-repo --out ./packet.md --stack node --tiers A,B
# explicit: write to ./packet.md, force node stack, only run Tier A and B checks

closeread audit ./my-repo --dry-run
# prints the scanner plan without executing: "would run osv-scanner, gitleaks, rg env-fallback pattern, jq license parse"

closeread audit ./my-repo --section sca
# run only one section (SCA) instead of the full packet; useful for iterative work

closeread audit ./my-repo --json > findings.json
# machine-readable, for downstream tooling
```

The `--section` flag matters because the packet has 10+ sections, each runnable independently, and a founder iterating on one finding does not need to wait for the full packet to regenerate. The smoke tests on Coolify, Mealie, and Papermark show that the SCA section alone is enough to start a conversation; gating that behind a full-packet regen is the wrong shape.

### 5. Replace `closeread-audit-mcp`'s `repo_path: str (absolute path)` requirement with sensible defaults

The MCP server scaffold at `mcp-server/README.md` describes the `audit_repo` tool as `audit_repo(repo_path: str)` requiring an absolute path. In practice, a user invoking the MCP from inside Cursor at the root of their repo has to type `/Users/me/projects/myrepo/` every time. Three issues:

1. Cursor (and most IDE-MCP clients) already knows the workspace root. The MCP should default to that.
2. "Absolute path" is a constraint that almost-always trips a user the first time. Most users type the relative path their shell would accept.
3. The tool gives no feedback on what it's about to scan before scanning. A founder pointed at the wrong directory loses 10 minutes per failed run.

**Before:**
```python
audit_repo(repo_path="/Users/founder/projects/mealie")
# either runs or fails with "FileNotFoundError" if path wrong
```

**After:**
```python
audit_repo()
# defaults to MCP client's workspace root; prints "auditing /Users/founder/projects/mealie (auto-detected from workspace)"

audit_repo(repo_path="./mealie")
# resolves relative to client workspace; expands to absolute internally

audit_repo(repo_path="./mealie", dry_run=True)
# returns the scanner plan without executing; lists which appendices would fire, estimated runtime

audit_repo(repo_path="./mealie", sections=["sca", "credentials"])
# runs only the named sections
```

The `dry_run=True` option matters double in MCP context: an LLM agent might invoke `audit_repo` against the wrong path, and the dry_run gives the human-in-the-loop a chance to catch it before the deterministic scanners spin up for 4 minutes.

### 6. Add `--verify-only` and `--print-cmd` to `audit-bootstrap.sh` (and the eventual `closeread doctor`)

Two missing modes a contributor will want in the first 10 minutes:

**`--verify-only`**: run the present-check but skip the install hint output. Use case: scripts that want to gate on "all required tools present" without printing 40 lines of suggested installs. Exit 0 if all present, exit 1 with one-line summary if anything missing.

**`--print-cmd`**: print the exact install command for the missing tools, one per line, machine-readable. Use case: a contributor copy-pastes the line into their own shell, or pipes the output into another script. Today they have to visually scan the 40-line output for the `install:` lines.

**Before:**
```bash
./bin/audit-bootstrap.sh
# 40 lines of mixed status + install hints
```

**After:**
```bash
./bin/audit-bootstrap.sh --verify-only
# exit 0, no output
# (or)
# exit 1, "missing: osv-scanner, pip-audit"

./bin/audit-bootstrap.sh --print-cmd
# brew install osv-scanner
# pipx install pip-audit
# (just the commands, copy-pasteable, no commentary)
```

These compose with each other: a CI job runs `--verify-only`, and a developer fixing the failure runs `--print-cmd | sh` if they trust it (or visually inspect first).

### 7. Make Ruby-stack handling friendly instead of cryptic

The current bootstrap script handles the macOS system-Ruby permission issue with a comment block and `--user-install` flags, but the user-facing output is a wall of mixed gem-install errors when the user runs `--install` on a clean macOS box without rbenv or homebrew Ruby. The known issue documented in `MEMORY.md` (`/Library/Ruby/Gems/2.6.0` permission error) hits every new contributor on macOS.

**Before:**
```bash
./bin/audit-bootstrap.sh --install --stack ruby
# === Appendix D: Ruby ===
#   ✓ ruby (runtime (>=3.2 expected))
#   ✓ bundle (Bundler (comes with Ruby))
#   ✗ bundler-audit (CVE scanner)
#     installing: gem install --user-install bundler-audit
# ERROR:  While executing gem ... (Errno::EACCES)
#     Permission denied @ rb_sysopen - /Library/Ruby/Gems/2.6.0/...
# (cryptic, user does not know what to do)
```

**After:**
```bash
./bin/audit-bootstrap.sh --install-missing --stack ruby
# === Appendix D: Ruby ===
# Detected: macOS system Ruby 2.6 (Apple, locked)
# Required: Ruby 3.2+ for current brakeman; pinning to brakeman 5.4.1 for compatibility
# Recommended: install brew Ruby first (`brew install ruby`) for cleaner gem paths
# Continue with system Ruby + --user-install? [Y/n]:
```

The script should detect the macOS-system-Ruby case explicitly (it already knows the version via `ruby -e 'print RUBY_VERSION'`) and surface the recommendation BEFORE the install attempt fails. The current code prints a PATH warning AFTER attempting installs; that order is backwards.

Also: the script should ship a `--ruby-runtime auto|system|brew|rbenv` flag so a contributor can override. Today the runtime is implicit.

### 8. Add `closeread --version` and a `--debug` flag that prints provenance

There is no version flag anywhere in the current surface. A user filing a bug against `audit-bootstrap.sh` has no canonical way to say "I ran version X." A user filing a bug against the MCP server has no way to say "I ran MCP version 0.1.0 against closeread 0.3.2 against repo Y." Both surface the same root issue: the tooling does not announce itself.

**Before:**
```bash
./bin/audit-bootstrap.sh --version
# (no such flag, script ignores it and runs full scan)
```

**After:**
```bash
./bin/audit-bootstrap.sh --version
# closeread audit-bootstrap 0.4.0 (methodology v2, commit a1b2c3d, built 2026-05-24)

closeread --version
# closeread 0.3.2 (Free Guy, Ed25519 fingerprint 6b4ff4a0..., signed by closeread.io/.soul)

closeread audit ./my-repo --debug
# prints provenance for every scanner: gitleaks 8.18.2, osv-scanner 1.7.3, semgrep 1.45.0
# also prints the audit-id, the methodology version, the .soul signature being applied to outputs
```

The `--debug` mode unlocks the methodology's defining promise: every finding is reproducible. A debug-mode invocation lets the user (or buyer's counsel) re-run the exact same scanners at the exact same versions weeks later and check the result.

---

## Cross-cutting patterns

Across all 8 changes the same patterns repeat. A contributor working on any of them should follow these:

- **Every destructive or non-idempotent action gets a `--dry-run`.** No exceptions. The script tells the user what it will do before doing it. Items 1, 4, 5, 6 all share this.
- **Every silent default gets named.** Items 2 (`--stack auto`), 5 (workspace-root default), 7 (`--ruby-runtime auto`) all replace implicit behavior with a flag that documents itself in `--help`.
- **Every flag gets a `--help` example.** The current `audit-bootstrap.sh` header comments document the flags. The eventual `closeread --help` output must do the same for every subcommand.
- **Every format choice gets a flag.** Item 3 (`--format pretty/ascii/json`) is the pattern. Apply to `closeread audit --output md|json|pdf` similarly.
- **Every version-able thing reports its version.** Item 8. Includes the script, the CLI, the MCP servers, the methodology version embedded in packets.
- **Tab-completion ships in the repo, not only on PyPI.** A contributor who clones the repo should get completions working with one `source completions/zsh/_closeread` line.

---

## What this audit deliberately does NOT propose

Out of scope for first-PR-able friction reduction, recorded so future-me does not re-propose them prematurely:

- **Configuration files (`.closereadrc`).** Tempting, but every config file is a new failure mode. Defer until users actually ask. Flags-only until v1.0.
- **Interactive TUI mode.** A `closeread audit` with prompts and a progress bar is appealing but a contributor cannot ship it in one PR. Defer to v0.2+.
- **Sub-commands beyond `audit`, `doctor`, `verify`.** Tempting to add `closeread compare`, `closeread refresh`, `closeread sign` immediately. Defer until the primary surface is solid. Three subcommands is enough for v0.1.
- **Telemetry.** The `mcp-server/pyproject.toml` description explicitly says "no telemetry." Honor that promise. Any "let us count installs" instinct gets deferred indefinitely.

---

## How a contributor should consume this audit

A contributor opening a PR against this directory picks one or more changes above. Each change is independently shippable. The recommended sequencing for a contributor with no prior context:

1. Start with #6 (`--verify-only` + `--print-cmd`). Two flags, ~20 lines of shell, no behavior change for existing users, immediate ergonomic win. Good first PR.
2. Then #2 (the `--stack` shift bug). One-line fix in the arg loop, plus tests. Removes a class of confused-new-user reports.
3. Then #3 (`--format` flag). 50 lines of refactor in the `status()` function. Adds JSON output. Unlocks #4.
4. Then #1 (rename `--install` to `--install-missing`, add `--dry-run`). Touches the install path; needs care.
5. #4 (`closeread audit` top-level command) is the big one. Should ship over multiple PRs, one section at a time, gated on the methodology repo's reference implementation landing.
6. #5, #7, #8 land independently of the above ordering.

Each PR should reference this audit by section number ("implements change #2 from `cli-ergonomics-audit-v1.md`") so the changelog tells the story of the surface getting friendlier release by release.

---

## Validation criteria

This audit is ready to ship as guidance to contributors when:

- [ ] At least 6 of the 8 changes have linked GitHub issues with `good-first-issue` label
- [ ] The recommended sequencing in "How a contributor should consume this audit" is verified against the actual state of `bin/audit-bootstrap.sh` at the time the issues are filed
- [ ] One of the 8 changes has a working reference PR demonstrating the pattern (recommended: #6, the smallest)
- [ ] The audit doc is linked from `reference-cli/README.md` so a contributor lands on it before opening an issue of their own

When all four conditions hold, this audit has done its job: it has converted "the CLI surface is rough" into 6+ concrete merge-able changes a new contributor can ship without further consultation.
