# Handoff — end of Round 6

Written 2026-11-23 for the session that does Round 7. Standing rules for every
session are in `CLAUDE.md` (read it first); this file covers only the state at
the end of Round 6. Older handoffs (`handoff-round-1.md` … `handoff-round-5.md`)
still describe earlier rounds; where they disagree with this file, this file
wins.

## Current state

- Requirements R1–R11 (`problem.md`) are implemented, specified in `spec.md`
  (now titled "Rounds 1–6") and tested. Round 6 added **R11**: a `.gitignore`
  that is a symbolic link is skipped. The link is not followed, its rules are
  not applied, and RepoLens warns about it on stderr and in the JSON.
- **173 tests pass** on Python 3.9.6 (`pytest -q`, ~0.3 s): 149 from Rounds
  1–5 and 24 new ones in `tests/test_r11_symlinked_gitignore.py`. None skip
  on macOS as a normal user.
- **Two earlier tests were changed**, both in `tests/test_r10_json.py`:
  `test_r10_top_level_keys_in_order` and
  `test_r10_exact_output_for_basic_fixture` now include the new last key
  `symlinked_gitignores`. No other earlier test changed.
- Round 6 commits, in order: `6c1e2a3` spec, `fcf637c` R11 code + tests,
  `7bc2794` decision 0006, `a397bc0` README. This handoff and any
  `CLAUDE.md` edits were left uncommitted for the user to review.
- Code layout (`repolens/`, ~631 lines):
  - `scanner.py`: `discover()` checks `(here / ".gitignore").is_symlink()`
    whenever `.gitignore` appears in `filenames` **or** `dirnames`. If it is a
    link, the path goes in the new `symlinked_gitignores` list and the file is
    not opened. Otherwise the file is read as before. `Discovery` and
    `ScanResult` each gained a `symlinked_gitignores` field (default empty).
  - `report.py`: `format_json()` gained a fifth optional argument,
    `symlinked_gitignores`, written as the **last** key.
    `format_report()` is unchanged.
  - `cli.py`: prints `Warning: skipped .gitignore that is a symlink: <path>`
    for each link, after the other two warning types, and passes the list to
    `format_json()`.
  - `gitignore.py`: unchanged.
- Decision records: `0001`–`0005` as before, plus `0006` (detect the link with
  `lstat`/`is_symlink()` during the walk, for every kind of target). The next
  number is `0007`.
- README: the JSON example has the new key. There is one new paragraph about
  the warning, and the `note`/warnings sentence now names
  `symlinked_gitignores`. The two table examples are unchanged and were
  checked against real output.

## How to run

From the repository root:

```
source .venv/bin/activate
python -m repolens <path>                       # e.g. python -m repolens tests/fixtures/basic
python -m repolens <path> --top N               # only the N largest files (R9)
python -m repolens <path> --format json         # report as JSON (R10)
python -m repolens <path> --format json --top N # JSON, N largest files
pytest                                          # or pytest -q; pytest tests/test_r11_symlinked_gitignore.py for Round 6
```

Fresh setup if `.venv` is missing:
`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

## Decisions made in Round 6 and why

Checked before asking: git 2.50.1 (installed here) ignores a symlinked
`.gitignore` and prints
`warning: unable to access '.gitignore': Too many levels of symbolic links`.
It does the same for a broken link.

Decided by the user (asked before any code was written):

1. **Warn on stderr and list the links in the JSON.** Chosen over a
   stderr-only warning and over skipping silently. This matches how the R7
   and Round 4 warnings already work in both formats.
2. **New wording**: `Warning: skipped .gitignore that is a symlink: <path>`.
   Chosen over reusing `cannot read .gitignore`, so the user can see why the
   rules were not used.

Decided in this session (the user was told at the end of Round 6):

3. **JSON key `symlinked_gitignores`, placed last** (after `top`), so the
   Round 5 key order is unchanged for existing readers. It is `[]` when there
   are no links.
4. **stderr order**: inaccessible folders, then unreadable `.gitignore`
   files, then symlinked `.gitignore` files, each sorted by path.
5. **A broken `.gitignore` link or link loop now gets the R11 warning**, not
   `cannot read .gitignore`, and is no longer in `unreadable_gitignores`.
   This is a behaviour change for that case.
6. **Every kind of link is skipped**: to a file inside or outside the scanned
   folder, to a folder, broken, or a loop. A link to a folder sits in
   `dirnames` and still gets a warning, as in git.
7. **Hard-linked `.gitignore` files are still read**, because they are not
   symbolic links.
8. **Exit status stays 0 and there is no `Incomplete:` line**, because no
   folder was missed. The table on stdout is unchanged.
9. **No warning for links inside a default-skipped or ignored folder**,
   because those folders are never entered.
10. **Detection by `is_symlink()` before reading** (decision 0006). Rejected
    alternatives: `O_NOFOLLOW` + `ELOOP` (not available on Windows, and the
    error code is ambiguous), skipping only links that point outside the
    folder (would need to follow the link), and checking only `filenames`
    (would miss links to folders).
11. **Optional last argument on `format_json()`, and dataclass fields with
    defaults**, so code that calls either the old way still works.
12. **Test that the target is never opened**: the target is made unreadable
    (`chmod 000`). If it were opened, the warning would say "cannot read".
    This test is permission-based. All R11 tests are in one new file built in
    `tmp_path`, and the whole module skips on Windows.

## Unresolved / known gaps

None of these is a failing test. Each needs a spec decision before code changes.

- **Check-then-read race**: if `.gitignore` is replaced by a link between the
  `is_symlink()` check and the read, the link is followed. Decision 0006
  describes a possible fix: `O_NOFOLLOW` where available.
- **Only `.gitignore` itself is checked.** Folder symlinks are never followed
  (R1), so a `.gitignore` reached through a linked folder cannot happen.
  However, the scanned root itself may be a path through a symlink (for
  example macOS `/tmp`), and that is allowed.
- **R11 tests have only run on macOS.** They skip on Windows, where creating
  symlinks needs privileges. They have not been tried on Linux.
- **No automatic comparison with git.** Git's behaviour was checked by hand
  on the root case only (file link and broken link).
- **No schema or version key in the JSON** (carried over from Round 5). The
  shape has now grown once: keys were added at the end, not renamed.
- **Still open from Round 5**: summary sums exist in both renderers; `note`
  values come straight from `FileStats.note`; undecodable file names are
  untested; the README JSON example is shortened (`...`), so it is not valid
  JSON as printed.
- **Still open from Round 4**: matching is case-sensitive, unlike git's macOS
  default; tracked-but-ignored files are skipped; `.git/info/exclude` and
  global excludes are not read; `gitignore.py` has no direct unit tests;
  performance has not been measured. (The symlinked-`.gitignore` gap from
  Round 4 is now closed by R11.)
- **Still open from Round 3**: the "Showing the 1 largest of 1 files"
  grammar; no upper limit on N; `--top` ranks by LOC only.
- **Still open from Round 2** (see `handoff-round-2.md`): no test for the
  `chmod 444` folder case; the root-folder branch of `on_error` is untested;
  a link into a skipped folder is counted; never run on Windows; only `.py`
  files are scanned.

## Warnings for the next session

- **There are three warning types now**, each with a fixed stderr position
  and its own JSON list. A fourth type needs a decision on its stderr
  position, a JSON key (added last) and tests that compare
  `err.splitlines()` exactly.
- **`format_json()` takes five arguments** (`stats, inaccessible_dirs,
  unreadable_gitignores, top, symlinked_gitignores`). `top` sits *between*
  the two `.gitignore` lists, so pass them by name or check the order.
  `format_report()` still takes a count, not a list.
- **The `.gitignore` check in `discover()` looks at both `filenames` and
  `dirnames`.** If the walk is rewritten (for example, to stop using
  `os.walk`), keep the case of a link to a folder.
- **Changing what counts as "unreadable" vs "symlinked"** changes both
  stderr text and JSON lists. Tests assert both.
- Earlier warnings still apply: `SKIP_DIRS` is checked before `.gitignore`;
  stdout may start with the `Showing` line (table mode, `--top`); the
  `Incomplete:` line stays last; invalid `--top` and `--format` raise
  `SystemExit`; `row_for()` splits on whitespace; macOS `/tmp` is a symlink
  to `/private/tmp`.

## Suggested first steps for Round 7

1. Read `CLAUDE.md`, `problem.md`, `spec.md`, this file and `docs/decisions/`.
2. Activate `.venv`, run `pytest`, and confirm 173 passed.
3. Read the Round 7 requirements in `problem.md`. Ask the user about anything
   unclear before writing code, including whether any new output must also
   appear in the JSON (R10) and where any new warning goes in the stderr
   order.
