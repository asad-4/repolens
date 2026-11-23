# Handoff — end of Round 3

Written 2026-11-22 for the session that does Round 4. Standing rules for every
session are in `CLAUDE.md` (read it first); this file covers only the state at
the end of Round 3. Older handoffs (`handoff-round-1.md`, `handoff-round-2.md`)
still describe Rounds 1–2; where they disagree with this file, this file wins.

## Current state

- Requirements R1–R9 (`problem.md`) are implemented, specified in `spec.md`
  (now titled "Rounds 1–3") and tested. **73 tests pass** on Python 3.9.6
  (`pytest -q`, ~0.15 s): 53 from Rounds 1–2, 20 for R9
  (`tests/test_r9_top.py`; one test is parametrized over 5 bad values).
- Last commit: `192946f README: document --top N (R9) with an example run`.
  Not committed: this file and the `CLAUDE.md` edit (left for the user to
  review).
- Round 3 commits, in order: `13178d9` spec, `75d7d95` R9 code + tests,
  `1ca1278` decision 0003, `192946f` README.
- Code layout (`repolens/`, ~320 lines):
  - `cli.py` — argparse. **New:** `--top N` option with the `_positive_int`
    type (R9). Passes `args.top` (or `None`) to `format_report`.
  - `scanner.py` — **unchanged in Round 3.** `discover()`, `find_python_files()`,
    `scan() -> ScanResult(files, inaccessible_dirs)`, `count_loc`,
    `count_definitions`, `analyze_file`.
  - `report.py` — **new:** `largest_files(stats, n)` sorts by `(-loc, path)` and
    keeps the first n. `format_report(stats, inaccessible_dirs=0, top=None)`:
    the table uses the shown rows, the summary always uses the full `stats`.
- Decision records: `0001` (ast/tokenize), `0002` (device+inode, R8), `0003`
  (apply `--top` when rendering, not in the scanner). The next number is `0004`.

## How to run

From the repository root:

```
source .venv/bin/activate
python -m repolens <path>                 # e.g. python -m repolens tests/fixtures/basic
python -m repolens <path> --top N         # only the N largest files (R9)
pytest                                    # or pytest -q
```

Fresh setup if `.venv` is missing:
`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

## Decisions made in Round 3 and why

Decided by the user (asked before any code was written):

1. **Ties on LOC are ordered by relative path** — same order as the normal
   report, so output is deterministic.
2. **N must be a whole number ≥ 1.** `0`, negatives, non-numbers and a missing
   N are argparse usage errors (stderr, exit 2), like other bad arguments.
3. **A note line says the table is cut short:**
   `Showing the K largest of M files (ranked by lines of code).` — so a table
   with fewer rows than `Files scanned:` is not confusing.
4. **Without `--top`, output is exactly as before** (all files, sorted by path).

Decided in this session (the user was told at the end of Round 3):

5. **Rows are chosen in `format_report()`, not in the scanner.** Recorded in
   `docs/decisions/0003-apply-top-n-when-rendering-the-report.md`. Why: the
   summary keeps its old code and input, so it cannot drift from a run without
   `--top` (a test compares the two summaries); `scan()` stays unchanged.
6. **The note line** is the first line of stdout, followed by a blank line;
   K = `min(N, M)`, so `--top 50` on 4 files says "4 largest of 4". It is
   printed even when N covers every file.
7. **No note line when no Python files are found** — output is identical to a
   run without `--top`.
8. **Ties at the cut-off are not extended:** exactly K rows, even if the next
   file has the same LOC.
9. **Error text:** `argument --top: must be a whole number of 1 or more, got '0'`.
10. **`--top` may come before or after the path** (argparse default).
11. **`(parse error)` / `(unreadable)` files are ranked** by the LOC on their row
    (0 for unreadable) and keep their marker.
12. **R7 warnings and the `Incomplete:` line still appear with `--top`.**
13. `spec.md` R2 now points to R9 for the changed order; the README got a
    second example (`--top 2`).

## Unresolved / known gaps

None of these is a failing test. Each needs a spec decision before code changes.

- **Grammar: "Showing the 1 largest of 1 files".** The note always says
  "files", even for one file. Not specified; fixing it changes an exact string
  asserted in `test_r9_prints_showing_line_first` and friends.
- **The R9 tests were written before the code but never run against the old
  code** to see them fail. They pass now; they were not shown to fail first.
- **`largest_files()` has no direct unit test.** It is only tested through the
  CLI (`run_cli`).
- **No `--top` for other metrics** (functions, classes). R9 ranks by LOC only;
  the option name `--top` would need care if a sort key is added later.
- **No upper limit on N.** A huge N (e.g. 10^20) is accepted and shows every
  file. Fine today; noted in case a limit is ever wanted.
- **Still open from Round 2** (see `handoff-round-2.md`): no automated test for
  the `chmod 444` folder case; the root-folder branch in `discover()`'s
  `on_error` is untested; a link into a skipped folder (e.g. `.venv`) is
  counted; never run on Windows; speed on large trees not measured; only `.py`
  is scanned. No decision records yet for the R7 output contract or the wider
  R5 skip list.

## Warnings for the next session

- **stdout may now start with the `Showing` line**, not the `File` header. Code
  or tests that assume line 0 is the table header must handle `--top`. The
  R9 tests use a `table_paths()` helper that finds the `---` separator line
  instead of counting lines.
- **`format_report()` has three parameters now** (`stats`, `inaccessible_dirs`,
  `top`). Always pass the **full** file list as `stats`; passing an already-cut
  list would make the summary wrong, which is exactly what R9 forbids.
- **The `Incomplete:` line is still the last line of stdout when present**
  (tested with and without `--top`). Put new summary lines before it.
- **Two R9 tests are permission-based** (`test_r9_unreadable_file_ranks_with_zero_loc`,
  `test_r9_r7_warnings_and_incomplete_line_still_shown`) and skip as root or
  on Windows, like the R3/R6/R7 ones.
- **Invalid `--top` values raise `SystemExit`** inside `main()` (argparse), so
  `run_cli` does not return for them; tests use `pytest.raises(SystemExit)`.
  The same is true of the R6 wrong-argument-count case.
- Earlier warnings still apply: `scan()` returns a `ScanResult`, not a list;
  `row_for()` splits on whitespace (no spaces in paths, ignores notes); macOS
  `/tmp` is a symlink to `/private/tmp` (don't `resolve()` files without the
  root).

## Suggested first steps for Round 4

1. Read `CLAUDE.md`, `problem.md`, `spec.md`, this file and `docs/decisions/`.
2. Activate `.venv`, run `pytest`, confirm 73 passed.
3. Read the Round 4 requirements in `problem.md`; ask the user about anything
   unclear (and, if relevant, the gaps above) before writing code.
