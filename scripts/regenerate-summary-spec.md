# Spec: `regenerate_summary.py`

Auto-regenerate `SUMMARY.md` for the closeread-io-methodology mdBook by walking
the repo directory tree and inferring chapter structure from path depth.

**Target length:** under 100 lines of Python.
**Runtime:** stdlib only (pathlib, os, sys, re).
**Idempotent:** safe to run on every commit; produces byte-for-byte identical output
when nothing has changed.

---

## Problem

`SUMMARY.md` is the mdBook table of contents. It must be maintained manually
today. When a contributor adds a finding, appends a stack appendix, or creates
a new specialist spec, the file goes stale unless they remember to edit it. CI
has no way to catch drift short of a full mdBook build, which takes 20+ seconds.
The fix is a script that regenerates `SUMMARY.md` from the directory tree in
under one second and can be wired into a pre-commit hook.

---

## Inputs and outputs

| Item | Value |
|---|---|
| Entry point | `scripts/regenerate_summary.py` |
| Called from | repo root: `python scripts/regenerate_summary.py` |
| Output | `SUMMARY.md` in the repo root (overwritten in-place) |
| Dry-run flag | `--dry-run` prints to stdout, does not write |
| Check flag | `--check` exits 1 if the current SUMMARY.md differs from what would be generated (CI gate) |

---

## Directory structure contract

The script must understand this repo's layout conventions:

```
README.md                    # root intro -- rendered as [Introduction](README.md)
SUMMARY.md                   # the file being regenerated -- skip
CONTRIBUTING.md              # top-level project files -- section "Project"
CODE_OF_CONDUCT.md           # same
methodology/
  README.md                  # section header
  01-philosophy.md           # numbered: sort numerically, strip leading digits for title
  specialists/               # sub-section at depth 2
    api-versioning-*.md
findings-library/
  README.md                  # section header
  polyglot/                  # sub-section grouping
    *.md
  node/
    *.md
appendices-by-stack/
  README.md
  node/README.md             # each stack is a leaf entry titled by dirname
findings/                    # hypothetical future top-level section
lessons/
  README.md
reference-cli/
  README.md
  mcp-server/README.md
  verify-mcp/README.md
```

Depth rules:
- Depth 0 files (root `*.md`) -- rendered as top-level entries.
- Depth 1 directories -- rendered as `# Section` headers; their `README.md`
  becomes the section overview entry.
- Depth 2 directories -- rendered as indented sub-group entries under their
  parent section.
- Depth 3+ directories -- treated as leaves; each contains a `README.md` used
  as the entry. Sub-files within depth-3 dirs are not surfaced in SUMMARY (too
  granular for a TOC; they appear in-page).

---

## Edge cases

### README.md vs index.md

mdBook accepts either as a section index. The script checks for `README.md`
first; falls back to `index.md`. If neither exists, the directory is surfaced
without a hyperlink (plain text header). This matches mdBook behavior where a
section header with no linked file is valid.

### Hidden files and directories

Any path component starting with `.` is skipped. This excludes `.github/`,
`.git/`, `.summary-ignore`, and any dotfiles. Applies at every depth.

### `.summary-ignore`

If `.summary-ignore` exists in the repo root, the script reads it as a
newline-delimited list of glob patterns (same syntax as `.gitignore`, subset:
no negations, no `**` -- just prefix and suffix wildcards). Any `.md` file
whose repo-relative path matches a pattern is excluded from output. This lets
contributors park work-in-progress files in the tree without polluting the TOC.

Example `.summary-ignore`:
```
sample-set/*
scripts/*
```

Files matching these patterns are silently skipped. The `SUMMARY.md` file
itself is always excluded regardless of `.summary-ignore`.

### Numeric filename prefixes

Files named `01-philosophy.md`, `02-reliability.md`, etc. are sorted by the
leading integer, then the integer and the first hyphen are stripped when
inferring the display title. Remaining kebab-case slug is title-cased:
`02-reliability.md` -> `Reliability`. Files without a numeric prefix are sorted
alphabetically by filename within their directory.

### Title inference

When a file has no leading number, the title is derived from the filename stem
(no extension) by replacing hyphens with spaces and title-casing each word:
`committed-env-file-in-repository.md` -> `Committed env file in repository`
(only the first word is capitalized; subsequent words follow Python's
`str.title()` with a manual override that lowercases connector words: `in`,
`the`, `a`, `an`, `of`, `with`, `and`, `or`, `for`, `to`, `at`, `by`).

Directories that contain a `README.md` with a `# Title` first line use that
H1 as the display title instead of the directory name.

### Files to always exclude

Regardless of `.summary-ignore`, the script unconditionally skips:

- `SUMMARY.md`
- `LICENSE` (no `.md` extension; already excluded, noted for clarity)
- Any file already excluded by hidden-path rule

The `# Project` section (CONTRIBUTING.md, CODE_OF_CONDUCT.md) is pinned to the
bottom of the output, after a horizontal rule separator, matching the current
hand-maintained convention.

---

## Output format

The generated `SUMMARY.md` follows mdBook spec exactly. Key formatting rules:

1. Top line: `# Summary` (literal, no trailing space)
2. Blank line after `# Summary`
3. Intro line: `[Introduction](README.md)` (unindented, no bullet)
4. Blank line
5. Each top-level section: `# Section Name` on its own line, followed by a
   blank line
6. Section entries: `- [Title](path/to/file.md)` (no leading spaces)
7. Sub-entries: `  - [Title](path/to/file.md)` (2-space indent per depth level)
8. Sub-sub-entries: `    - [Title](...)` (4 spaces)
9. Horizontal rule `---` before the pinned `# Project` section
10. Final line: blank

No trailing spaces on any line. Line endings: LF (`\n`). The script always
writes with `open(..., "w", newline="\n")`.

---

## Implementation outline (under 100 lines)

```python
#!/usr/bin/env python3
"""Regenerate SUMMARY.md for the closeread-io-methodology mdBook."""

import argparse, fnmatch, os, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent          # repo root

# ---- config -----------------------------------------------------------------
INTRO_FILE      = "README.md"
OUTPUT_FILE     = "SUMMARY.md"
IGNORE_FILE     = ".summary-ignore"
ALWAYS_SKIP     = {OUTPUT_FILE, "SUMMARY.md"}
PINNED_BOTTOM   = ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md"]
SECTION_ORDER   = [                          # explicit top-level order
    "methodology", "packet-template", "findings-library",
    "appendices-by-stack", "reference-cli", "lessons",
]
CONNECTOR_WORDS = {"in","the","a","an","of","with","and","or","for","to","at","by"}

# ---- helpers ----------------------------------------------------------------
def load_ignore(root: Path) -> list[str]:
    p = root / IGNORE_FILE
    if not p.exists(): return []
    return [l.strip() for l in p.read_text().splitlines() if l.strip()]

def is_ignored(rel: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat): return True
    return False

def title_from_stem(stem: str) -> str:
    stem = re.sub(r"^\d+-", "", stem)       # strip leading numeric prefix
    words = stem.replace("-", " ").split()
    return " ".join(
        w if (i > 0 and w in CONNECTOR_WORDS) else w.capitalize()
        for i, w in enumerate(words)
    )

def readme_title(d: Path) -> str | None:
    for name in ("README.md", "index.md"):
        p = d / name
        if p.exists():
            first = p.read_text(errors="replace").splitlines()
            if first and first[0].startswith("# "):
                return first[0][2:].strip()
    return None

def entry(rel: str, title: str, depth: int) -> str:
    indent = "  " * depth
    return f"{indent}- [{title}]({rel})"

def section_files(d: Path, ignore: list[str], depth: int) -> list[str]:
    lines = []
    index = next((d/n for n in ("README.md","index.md") if (d/n).exists()), None)
    if index:
        rel = index.relative_to(ROOT).as_posix()
        title = readme_title(d) or title_from_stem(d.name)
        lines.append(entry(rel, title, depth))
    for child in sorted(d.iterdir()):
        if child.name.startswith("."): continue
        rel = child.relative_to(ROOT).as_posix()
        if is_ignored(rel, ignore): continue
        if child.is_dir():
            lines.extend(section_files(child, ignore, depth + 1))
        elif child.suffix == ".md" and child != index:
            if child.name in ALWAYS_SKIP: continue
            lines.append(entry(rel, title_from_stem(child.stem), depth))
    return lines

# ---- main -------------------------------------------------------------------
def generate(root: Path) -> str:
    ignore = load_ignore(root)
    parts = ["# Summary\n", f"[Introduction]({INTRO_FILE})\n"]
    for section_dir in SECTION_ORDER:
        d = root / section_dir
        if not d.is_dir(): continue
        header = readme_title(d) or title_from_stem(section_dir)
        parts.append(f"\n# {header}\n")
        parts.extend(ln + "\n" for ln in section_files(d, ignore, 0))
    parts.append("\n---\n\n# Project\n")
    for fname in PINNED_BOTTOM:
        p = root / fname
        if p.exists():
            parts.append(f"- [{title_from_stem(p.stem)}]({fname})\n")
    parts.append("- [License](LICENSE)\n")
    return "".join(parts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check",   action="store_true")
    args = ap.parse_args()
    out = generate(ROOT)
    if args.dry_run:
        sys.stdout.write(out); return
    if args.check:
        current = (ROOT / OUTPUT_FILE).read_text() if (ROOT / OUTPUT_FILE).exists() else ""
        if current != out:
            print("SUMMARY.md is stale. Run: python scripts/regenerate_summary.py", file=sys.stderr)
            sys.exit(1)
        return
    (ROOT / OUTPUT_FILE).write_text(out, newline="\n")
    print(f"Written: {ROOT / OUTPUT_FILE}")

if __name__ == "__main__":
    main()
```

This comes in at 88 lines including blank lines and comments.

---

## Example run against current repo state

Running `python scripts/regenerate_summary.py --dry-run` against the current
tree produces output equivalent to the hand-maintained `SUMMARY.md` with the
following differences that represent correct updates:

**Files now included that are missing from the current hand-maintained file:**

- `methodology/reflect-qa-harness-spec.md` -- Reflect QA harness spec
- `methodology/reviewer-calibration-study-design.md` -- Reviewer calibration
  study design
- `methodology/specialists/api-versioning-specialist-spec.md` -- Api versioning
  specialist spec
- `methodology/specialists/db-migration-risk-specialist-spec.md` -- Db migration
  risk specialist spec
- `methodology/specialists/license-compliance-specialist-spec.md` -- License
  compliance specialist spec
- `reference-cli/cli-ergonomics-audit-v1.md` -- Cli ergonomics audit v1
- `reference-cli/perf-profiling-plan-v1.md` -- Perf profiling plan v1

**Files excluded by `.summary-ignore` (to add on first run):**

```
sample-set/*
scripts/*
.github/*
```

The `sample-set/22-repo-synthesis-essay-v1.md` file should be in
`.summary-ignore`, not the SUMMARY. It is an audit artifact, not a doc page.
Similarly, `scripts/` should ignore itself.

**The current hand-maintained file has one structural issue:** in the
`findings-library` section, the polyglot and node subsections each point their
section-overview entry to the first finding file rather than a `README.md` that
summarizes the section. The script handles this by using `findings-library/README.md`
as the overview and then rendering each finding as a sub-entry. This produces
cleaner TOC structure.

---

## Integration

**Pre-commit hook** (`scripts/pre-commit-summary-check.sh`):

```sh
#!/usr/bin/env bash
set -euo pipefail
python "$(git rev-parse --show-toplevel)/scripts/regenerate_summary.py" --check
```

Wire via `.pre-commit-config.yaml` or symlink to `.git/hooks/pre-commit`.

**CI** (one job step after checkout):

```yaml
- name: Check SUMMARY.md is up to date
  run: python scripts/regenerate_summary.py --check
```

Fails the build if a contributor merged a new `.md` file without regenerating.

---

## Known limitations

1. Title inference is heuristic. Files with unusual names (version strings,
   camelCase) will get titles that need a manual override. The plan for this is
   a `SUMMARY-overrides.json` file that maps `relative/path.md` to display
   title; the script merges overrides after inference. Not implemented in v1.

2. The `SECTION_ORDER` list is hardcoded. Adding a new top-level directory
   requires updating the script. Acceptable for this repo's change rate.

3. Files deeper than depth 3 are silently ignored. If `methodology/specialists/`
   ever gains sub-directories, extend the recursion limit.

4. Title inference lowercases connector words mid-title but does not handle
   proper nouns (e.g. `tRPC` becomes `Trpc`). Fix: parse the H1 from each file
   when it exists. The outline above already does this for `README.md` files;
   extend it to all `.md` files in a v2.
