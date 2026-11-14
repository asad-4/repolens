# CLAUDE.md — standing rules for this repo

## Language and dependencies
- Python only: standard library plus pytest. No other third-party packages.
- Must run on Python 3.9: no `match` statements, no `X | Y` type hints
  (use `Optional[X]` / `Union[X, Y]` from `typing`).

## Tests
- Every test names the requirement ID it checks in its name,
  e.g. `test_r3_counts_async_functions`.
- Run `pytest` before every commit. Never commit failing tests.
- Run commands from the repo root with `.venv` activated (`source .venv/bin/activate`).
- Never "fix" files under `tests/fixtures/`: some are deliberately broken
  (syntax errors, unterminated strings). Keep `norecursedirs = fixtures` in `pytest.ini`.
- Build test trees that need symlinks, hard links, chmod or skipped folders
  (`.git`, `.venv`, …) in `tmp_path`, never in `tests/fixtures/`. Always restore
  permissions in a `finally` or fixture teardown, or pytest cannot clean up.
- Permission-based tests skip on Windows and as root; symlink tests skip on
  Windows. Use the existing `skipif` patterns.
- Commit new tests in the same commit as the code that makes them pass.

## Git
- Never edit `problem.md`.
- Never amend or undo a commit (no `git commit --amend`, `git reset`, `git revert`, or force-push).
- Never track `.venv`, `__pycache__` or `.jsonl` files.

## Project pointers
- Requirements: `problem.md` (source) and `spec.md` (precise, testable version).
  `spec.md` is one cumulative file: add each round's requirements as new
  sections and update the round range in its title.
- The README output example is copied by hand from
  `python -m repolens tests/fixtures/basic`; update it when stdout changes.
- Run: `python -m repolens <path>`. Test: `pytest`.
- Decisions: `docs/decisions/NNNN-*.md` (Y-statements).
- Handoffs between sessions: `handoff-round-N.md` at the repo root. At the start
  of a session, read the latest one.
