# 0004 — Match `.gitignore` rules with our own standard-library matcher, applied while walking

- Status: accepted
- Date: 2026-11-22
- Requirements: R5 (changed in Round 4), R7, R8

## Decision (Y-statement)

In the context of **making RepoLens respect `.gitignore` rules (ignored files,
folders, wildcard patterns and nested `.gitignore` files) on top of the fixed
R5 skip list**,
facing **a "standard library plus pytest only" rule, scans of folders that may
not be git repositories, and the need to prune ignored folders before entering
them (so that unreadable or huge ignored folders cost nothing and give no R7
warning)**,
we decided for **a small gitignore matcher in `repolens/gitignore.py` that
turns each pattern into a regular expression, with rules collected per folder
during the existing `os.walk` (parent rules first, then the folder's own) and
checked last-match-wins before a folder is entered or a `.py` file is kept**,
and neglected **running `git check-ignore` / `git ls-files` as a subprocess**,
**translating patterns with `fnmatch`**, **a third-party library such as
`pathspec`**, and **walking everything first and filtering the file list
afterwards**,
to achieve **git-compatible results (checked against `git check-ignore` on a
scratch repository) that work without git installed and outside any
repository, depend only on files inside the scanned folder, and leave the R7
and R8 logic unchanged**,
accepting that **we own about 150 lines of pattern code that must follow git's
rules by hand (edge cases such as an unclosed `[` were found only by comparing
with git), that matching is always case-sensitive even where git would use
`core.ignorecase`, and that git's other sources (`.git/info/exclude`, global
excludes, tracked-but-ignored files) are not considered**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Own regex-based matcher, applied during the walk (chosen)** | Standard library only. No git needed; works on plain folders and extracted archives. Ignored folders are never entered. Small pure functions, unit-testable through `find_python_files`. | We must reproduce git's syntax ourselves; any gap is a silent mismatch. |
| `git check-ignore --stdin` / `git ls-files -co --exclude-standard` | Exactly git's behaviour, including `core.ignorecase`, `info/exclude` and global excludes. | Needs git installed and a real repository; a plain folder would ignore nothing. Output would depend on machine settings and on files outside `<path>` (the user chose "inside scanned folder only"). Adds a subprocess and error handling for git failures. |
| `fnmatch.translate` per pattern | Less code. | Its `*` matches `/`, it has no `**`, anchoring, dir-only or negation rules, and its `[!...]` handling differs; we would wrap and patch most of it anyway. |
| Third-party `pathspec` | Mature, git-compatible. | Breaks the CLAUDE.md rule: standard library plus pytest only. |
| Walk everything, filter the list afterwards | Scanner loop unchanged. | Enters ignored folders (e.g. `build/`, `dist/`, a huge `data/`), which is slow and would print R7 warnings for unreadable folders the user asked to ignore. Cannot express git's "a `!` rule cannot re-include a file inside an ignored folder" without extra parent checks. |

## Consequences

- `discover()` keeps one rule list per visited folder; deeper rules come later
  in the list, so "last match wins" also gives deeper `.gitignore` files
  priority, as in git.
- The default R5 skip list is checked before `.gitignore`, so `!venv/` cannot
  bring `venv` back (the user's choice).
- An unreadable `.gitignore` is treated as empty and reported with
  `Warning: cannot read .gitignore: <path>` on stderr; `Discovery` and
  `ScanResult` gained an `unreadable_gitignores` field (default empty, so
  older callers still work).
- A symlink is matched by where the link is, not by its target, so a link
  outside an ignored folder still counts (R8 keeps one row per real file).
