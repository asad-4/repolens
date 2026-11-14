# Handoff — end of Round 1

Written 2026-11-14 for the session that does Round 2. Standing rules for every
session are in `CLAUDE.md`; this file covers only what is specific to the end of
Round 1.

## Current state

- All six Round 1 requirements (R1–R6 in `problem.md`, made precise in `spec.md`)
  are implemented and tested. **36 tests pass** on Python 3.9.6 (`pytest -q`, ~0.1 s).
- Last commit: `cb920ab Record decision 0001: count with ast/tokenize, not regex`.
  Working tree was clean before this handoff file and the `CLAUDE.md` edit were
  written (both are uncommitted, waiting for the user to review).
- Code layout (`repolens/`, ~200 lines total):
  - `cli.py` — argparse entry point, folder checks and `Error:` messages (R1, R6).
  - `scanner.py` — file discovery with `os.walk` + skip list (R1, R5), LOC via
    `tokenize` with a line-based fallback (R2), `def`/`async def`/`class` counts
    via `ast.walk` (R3). `FileStats` dataclass with an optional `note`
    (`"parse error"` or `"unreadable"`).
  - `report.py` — table and summary text (R2–R4).
  - `__main__.py` — enables `python -m repolens`.
- Tests: `tests/test_r1_scan.py` … `tests/test_r6_errors.py`, one file per
  requirement. Shared helpers in `tests/conftest.py`: `run_cli` (runs `main()`
  in-process, returns `(exit_code, stdout, stderr)`) and `row_for(stdout, path)`.
  Sample projects live in `tests/fixtures/` (`basic`, `broken`, `counts`, `loc`,
  `no_python`).

## How to run

From the repository root:

```
source .venv/bin/activate          # .venv already exists, pytest installed
python -m repolens <path>          # e.g. python -m repolens tests/fixtures/basic
pytest                             # or pytest -q
```

Fresh setup if `.venv` is missing: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

`pytest.ini` sets `testpaths = tests`, `pythonpath = .` and
`norecursedirs = fixtures`.

## Decisions made in Round 1 and why

1. **`ast` + `tokenize`, not regex** (recorded in
   `docs/decisions/0001-use-ast-and-tokenize-for-counting.md`). Counts agree with
   how Python reads the file: `#` inside a string is not a comment, `def` inside
   a docstring is not a function, async defs and methods are always found.
   Cost: files with syntax errors get 0 functions/classes plus `(parse error)`.
2. **Docstrings count as lines of code.** To the tokenizer they are string
   tokens, not comments. Stated explicitly in `spec.md` R2.
3. **Functions include methods and nested functions; lambdas excluded.** Classes
   counted at any nesting level. (`spec.md` R3.)
4. **One bad file never stops the scan.** Syntax error / undecodable bytes →
   `(parse error)`; permission denied on a single file → listed with zeros and
   `(unreadable)` (commit `9704cda`). Rationale: make the gap visible instead of
   silently dropping the file or crashing.
5. **Skip list is wider than `problem.md` R5.** `problem.md` names `.git`,
   `.venv`, `venv`, `__pycache__`; `spec.md` adds `.hg`, `.svn`,
   `.pytest_cache`, `.mypy_cache`, `.tox`, `node_modules` ("such as" in R5 was
   read as an open list). Exact-name match; the root folder is always scanned
   even if it is itself named e.g. `venv`.
6. **Deterministic output.** Files sorted by `/`-separated relative path.
7. **Error contract (R6).** One line starting `Error:` on stderr, nothing on
   stdout, exit 1; wrong argument count is argparse's usage message, exit 2.
8. **Symlinked directories are not followed** (`os.walk(followlinks=False)`) to
   avoid loops.

Only decision 1 has a decision record. Decisions 4 and 5 are arguably worth
their own `docs/decisions/` entries; the user has not asked for them yet.

## Unresolved / known gaps

These were found by checking behaviour at the end of Round 1 (verified with a
throwaway folder, not in the test suite). None is a failing test; each needs a
spec decision before code changes.

- **Unreadable subfolder is silently dropped.** If a folder *inside* the scanned
  tree has no read permission, `os.walk` skips it with no message, and its `.py`
  files simply don't appear. This is inconsistent with the `(unreadable)` rule for
  single files. `spec.md` does not cover this case.
- **Symlinked `.py` files are followed and counted.** A symlink `link.py → real/r.py`
  makes `r.py` appear twice and be counted twice in the totals. Only *directory*
  symlinks are excluded by the spec. Unspecified whether this is wanted.
- **Not tested:** that directory symlinks are not followed (behaviour is correct,
  there's just no test for it).
- **Only `.py` is scanned** (`.pyw`, `.pyi` ignored by design per `spec.md` R1).

## Warnings for the next session

- **`tests/fixtures/` contains deliberately broken Python** (`broken/bad_syntax.py`,
  `broken/unterminated.py`, and an undecodable file built in a test). Do not
  "fix" them. `norecursedirs = fixtures` in `pytest.ini` stops pytest from trying
  to collect them — don't remove it.
- **Exact numbers in tests depend on fixture contents.** Editing any fixture file
  changes LOC/function/class totals asserted in R2–R4 tests and the README example.
- **`row_for()` in `conftest.py` splits rows on whitespace**, so it breaks on
  paths that contain spaces (the program itself handles them fine). Use another
  approach if a test needs such a path.
- **Two tests are skipped as root or on Windows** (permission-based tests in R3
  and R6). If you run as root, they will show as skipped, not passed.
- **Results depend on the running Python's grammar.** On 3.9, a scanned project
  using `match` statements or other newer syntax shows `(parse error)`. This is
  expected and documented in decision 0001.
- **The README output example is hand-copied** from `python -m repolens
  tests/fixtures/basic`. If output format or that fixture changes, update it.
- **`spec.md` is titled "Round 1".** If Round 2 brings new requirements, decide
  with the user whether to extend it or start a new section.
- Not committed by this session: `handoff-round-1.md` and the `CLAUDE.md` edit.
  The user will review them and commit.

## Suggested first steps for Round 2

1. Read `CLAUDE.md`, `problem.md`, `spec.md`, then this file.
2. Activate `.venv`, run `pytest` and confirm 36 passed.
3. Ask the user for the Round 2 requirements, and whether to resolve the two
   gaps above (unreadable subfolders, symlinked files) first.
