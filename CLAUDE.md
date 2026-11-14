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

## Git
- Never edit `problem.md`.
- Never amend or undo a commit (no `git commit --amend`, `git reset`, `git revert`, or force-push).
- Never track `.venv`, `__pycache__` or `.jsonl` files.

## Project pointers
- Requirements: `problem.md` (source) and `spec.md` (precise, testable version).
- Run: `python -m repolens <path>`. Test: `pytest`.
- Decisions: `docs/decisions/NNNN-*.md` (Y-statements).
- Handoffs between sessions: `handoff-round-N.md` at the repo root. At the start
  of a session, read the latest one.
