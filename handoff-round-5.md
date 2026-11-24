# Handoff — end of Round 5

Written 2026-11-23 for the session that does Round 6. Standing rules for every
session are in `CLAUDE.md` (read it first); this file covers only the state at
the end of Round 5. Older handoffs (`handoff-round-1.md` … `handoff-round-4.md`)
still describe earlier rounds; where they disagree with this file, this file
wins.

## Current state

- Requirements R1–R10 (`problem.md`) are implemented, specified in `spec.md`
  (now titled "Rounds 1–5") and tested. Round 5 added **R10**: `--format json`
  prints the report as one JSON object with the same files and summary totals
  as the table.
- **149 tests pass** on Python 3.9.6 (`pytest -q`, ~0.25 s): 114 from Rounds
  1–4 and 35 new ones in `tests/test_r10_json.py`. None skip on macOS as a
  normal user. No earlier test was changed.
- Round 5 commits, in order: `2ce9c05` spec, `1802492` R10 code + tests,
  `fcbe5a9` decision 0005, `6d80ecc` README. This file is committed
  separately after them.
- Code layout (`repolens/`, ~605 lines):
  - `report.py` — **new `format_json(stats, inaccessible_dirs,
    unreadable_gitignores, top)`**. Picks rows with the existing
    `largest_files()` (same as the table), sums the summary over the full
    `stats` list, builds the object with `OrderedDict` in a fixed key order
    and returns `json.dumps(..., indent=2, ensure_ascii=True)`.
    `format_report()` is unchanged.
  - `cli.py` — new `--format` option (`choices=("table", "json")`,
    default `table`). Warnings are printed to stderr exactly as before in both
    formats; then either `format_json(...)` or `format_report(...)` is printed.
  - `scanner.py`, `gitignore.py` — unchanged in Round 5.
- Decision records: `0001` (ast/tokenize), `0002` (device+inode, R8), `0003`
  (`--top` applied when rendering), `0004` (own gitignore matcher), `0005`
  (JSON as one indented ASCII object built beside the table renderer). The
  next number is `0006`.
- README: usage line now shows `[--format {table,json}]`; new paragraph with a
  **shortened** JSON example (`...` stands for the remaining files) and a note
  on `note` values and warnings. The two table examples are unchanged.

## How to run

From the repository root:

```
source .venv/bin/activate
python -m repolens <path>                       # e.g. python -m repolens tests/fixtures/basic
python -m repolens <path> --top N               # only the N largest files (R9)
python -m repolens <path> --format json         # report as JSON (R10)
python -m repolens <path> --format json --top N # JSON, N largest files
pytest                                          # or pytest -q; pytest tests/test_r10_json.py for Round 5
```

Fresh setup if `.venv` is missing:
`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

## Decisions made in Round 5 and why

Decided by the user (asked before any code was written):

1. **One JSON object** with top-level keys `files`, `summary`,
   `inaccessible_folders`, `unreadable_gitignores`. Each file object has
   `path`, `lines`, `functions`, `classes`, `note`; `summary` has
   `files_scanned`, `lines_of_code`, `functions`, `classes`. Chosen over a
   flat list of files, which would drop the summary R10 asks for.
2. **`--top N` with JSON limits and ranks `files`** exactly like the table
   (N largest by LOC, ties by path); the summary still counts every file.
   Not "ignore `--top`" and not "reject the combination".
3. **Warnings go to stderr and into the JSON.** stderr keeps the same
   `Warning: …` lines as table mode; the same paths are listed in
   `inaccessible_folders` / `unreadable_gitignores`, so a program can see the
   scan was incomplete without reading stderr.
4. **`--format` accepts `table` (default) and `json`.** Any other value is an
   `argparse` usage error, exit 2.

Decided in this session (the user was told at the end of Round 5):

5. **A fifth top-level key, `top`** (last): N as an integer, or `null`.
   Replaces the information in the table's `Showing the K largest of M files`
   line together with `len(files)` and `summary.files_scanned`.
6. **No separate "files shown" key.** During the questions the user was told
   the JSON would record how many files were shown; that number is
   `len(files)`, and `spec.md` says so. Easy to add if wanted.
7. **No `incomplete` key.** A non-empty `inaccessible_folders` replaces the
   table's `Incomplete:` line — one source of truth instead of two.
8. **Fixed key order** (top level, file objects, summary) so output is stable
   and can be compared as text, not just as parsed data.
9. **`note` is `"parse error"`, `"unreadable"` or `null`** — the table's
   marker without brackets, `null` rather than a missing key, so every file
   object has the same keys.
10. **`indent=2` and `ensure_ascii=True`.** Readable in a terminal; pure ASCII
    so printing never fails on a non-UTF-8 terminal. Non-ASCII path
    characters appear as `\uXXXX` (parsers decode them back).
11. **Only JSON on stdout** in JSON mode: no `Showing…` line, no
    `No Python files found.` line. An empty scan gives `"files": []` and an
    all-zero summary. Output ends with a single newline (from `print`).
12. **Exit status 0** for a successful JSON run, warnings or not, as in table
    mode.
13. **R6 errors and argument errors stay plain text** on stderr in every
    format (exit 1 / 2, nothing on stdout) — no report exists to format.
    Format values are case-sensitive (`JSON` is rejected).
14. **`format_json()` is a separate function beside `format_report()`**
    (decision 0005), reusing `largest_files()`, with hand-chosen key names
    (`lines`, not the internal `loc`). Rejected: `dataclasses.asdict`
    (leaks internal names), JSON Lines (not one document; no memory saved
    since all stats are held anyway), compact JSON, a shared report model
    (refactor of heavily-tested table code for ~10 lines saved).
15. **Tests compare JSON with the table** on every fixture (`basic`,
    `broken`, `counts`, `loc`, `no_python`): same paths, order, numbers and
    totals. Three tests are permission-based (skip on Windows and as root);
    one skips on Windows (file name with `"` and `\`). Trees are built in
    `tmp_path`.
16. **README example is shortened** with `...`, so it is not valid JSON as
    printed; a complete example (`--format json --top 2` on the spec's
    three-file example folder) is in `spec.md`.
17. One decision record (0005). The user's four choices are in the spec, not
    in a separate record.

## Unresolved / known gaps

None of these is a failing test. Each needs a spec decision before code changes.

- **Summary sums exist twice** (`format_report()` and `format_json()`). The
  parametrised test catches drift on the fixtures, but a change to one
  renderer must be copied to the other.
- **`note` values come straight from `FileStats.note`.** Renaming a marker in
  the scanner silently changes the public JSON value too. Tests assert
  `"parse error"` and `"unreadable"`.
- **No schema or version key.** Scripts have nothing to check if the shape
  changes in a later round. Adding keys at the end is backward compatible;
  renaming or removing is not.
- **Undecodable file names not tested.** On Linux a non-UTF-8 name becomes a
  lone surrogate (`\udcxx`) in the path; `json.dumps` with `ensure_ascii`
  writes it as an escape that Python reads back but strict JSON parsers may
  reject. macOS (APFS) does not allow such names, so it was not tried. The
  table output path for such names was not checked either.
- **`unterminated.py` in `fixtures/broken`**: its JSON row is checked only
  through the table comparison, not by an explicit `note` assertion.
- **Whole report is built in memory** as one string before printing. Fine for
  normal repos; not measured on very large ones.
- **README JSON example is not a copy of real stdout** (shortened). The
  CLAUDE.md rule about hand-copied examples names only the two table
  commands, so it was not extended to JSON.
- **Still open from Round 4** (not raised with the user this round):
  a symlinked `.gitignore` is read, while git 2.32+ ignores it; matching is
  case-sensitive unlike git's macOS default; tracked-but-ignored files are
  skipped; no automatic comparison with git; no direct unit tests for
  `gitignore.py`; performance not measured.
- **Still open from Round 3**: "Showing the 1 largest of 1 files" grammar;
  `largest_files()` has no direct unit test (now used by both renderers); no
  upper limit on N; `--top` ranks by LOC only.
- **Still open from Round 2** (see `handoff-round-2.md`): no test for the
  `chmod 444` folder case; root-folder branch of `on_error` untested; a link
  into a skipped folder is counted; never run on Windows; only `.py` scanned.

## Warnings for the next session

- **JSON shape is a public contract.** Tests assert the exact key order and
  the full object for `tests/fixtures/basic`. Changing a key means changing
  spec, `tests/test_r10_json.py` and README together, and it breaks users'
  scripts — prefer adding keys at the end.
- **Any new per-file or summary value must be added to both renderers**, or
  the R10 "same files and totals" tests (and the requirement) break.
- **Keep stdout pure JSON in JSON mode.** Anything new printed to stdout
  (notices, progress) must go to stderr or be skipped when
  `args.format == "json"`; `test_r10_stdout_is_one_json_object` calls
  `json.loads` on the whole stdout.
- **Warnings still go to stderr in JSON mode** and tests compare
  `err.splitlines()` exactly; a new warning type needs a stderr order and,
  probably, a new JSON list.
- **`format_json()` takes the warning lists, `format_report()` takes a count**
  (`len(inaccessible_dirs)`); the signatures differ on purpose — don't swap
  the arguments.
- Earlier warnings still apply: no `.gitignore` under `tests/fixtures/`;
  `SKIP_DIRS` is checked before `.gitignore`; `Discovery`/`ScanResult` new
  fields need defaults; stdout may start with the `Showing` line (table
  mode, `--top`); the `Incomplete:` line stays last; invalid `--top` and
  `--format` raise `SystemExit`; `row_for()` splits on whitespace; macOS
  `/tmp` is a symlink to `/private/tmp`.

## Suggested first steps for Round 6

1. Read `CLAUDE.md`, `problem.md`, `spec.md`, this file and `docs/decisions/`.
2. Activate `.venv`, run `pytest`, confirm 149 passed.
3. Read the Round 6 requirements in `problem.md`; ask the user about anything
   unclear — and, if the round touches output, whether it must also appear in
   the JSON (R10) — before writing code. The open Round 4 gap (symlinked
   `.gitignore`) is still worth raising.
