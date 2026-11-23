# repolens — Specification (Rounds 1–4)

repolens is a command-line tool that gives a quick overview of a Python codebase:
which files exist, how big they are, and how many functions and classes they hold.

Source of requirements: `problem.md` (R1–R6 in Round 1, R7–R8 in Round 2, R9 in
Round 3, R5 changed in Round 4). This
document makes each requirement precise enough to test.

## Usage

```
python -m repolens <path> [--top N]
```

Exactly one positional argument: the folder to scan. The optional `--top N`
(R9) may appear before or after it.

## Requirements

### R1 — Accept a folder and scan Python files recursively

- The folder path is given as the single command-line argument.
- Every file whose name ends in `.py` inside that folder, at any depth, is scanned.
- Files with other extensions (`.txt`, `.pyc`, `.pyi`, …) are ignored.
- Symbolic links to directories are not followed (avoids infinite loops).
- A file is selected by the name of the directory entry: a symlink named `x.py`
  is scanned (its target's contents are measured); a symlink named `x` that
  points to `y.py` is not. Duplicates are merged as described in R8.

### R2 — Per-file relative path and lines of code

- For each scanned file, the output shows its path relative to the given folder,
  using `/` as the separator on every platform.
- Files are listed in sorted order by relative path, so output is deterministic.
  (`--top N` changes the order and number of rows; see R9.)
- **Lines of code (LOC)** = the number of lines that contain at least one Python
  token that is not a comment. Concretely:
  - blank / whitespace-only lines are not counted;
  - lines containing only a `#` comment are not counted;
  - a line with code followed by a trailing comment **is** counted;
  - a `#` inside a string literal does not make the line a comment;
  - docstrings and other string literals are code and **are** counted
    (they are not comments in Python's grammar).
- If a file cannot be tokenized (e.g. syntax error), LOC falls back to a simple
  rule: count lines that are non-blank and do not start with `#` after stripping.

### R3 — Count functions and classes, including async functions

- Functions = every `def` and `async def` in the file, at any nesting level
  (top-level functions, methods, nested functions).
- Classes = every `class` statement, at any nesting level.
- Lambdas are not counted as functions.
- If a file cannot be parsed (syntax error or undecodable bytes), its function
  and class counts are 0, it is marked in the output as `(parse error)`, and the
  scan continues. The program never crashes because of one bad file.
- If a single file inside the folder cannot be read (e.g. permission denied),
  it is still listed, with 0 for every count and the marker `(unreadable)`.

### R4 — Summary at the end

After the per-file list, a summary shows:

- total number of Python files scanned,
- total lines of code,
- total functions,
- total classes.

Totals are the sums of the per-file values. If no Python files are found, the
program prints `No Python files found.` followed by the summary with all zeros.

If one or more folders could not be accessed (R7), the summary ends with one
extra line:

```
  Incomplete:     N folder(s) could not be accessed (see warnings)
```

The line is absent when every folder was read.

### R5 — Skip unnecessary directories

Directories with the following names are skipped at any depth, together with
everything inside them:

`.git`, `.hg`, `.svn`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`,
`.mypy_cache`, `.tox`, `node_modules`

Matching is by exact directory name. The folder passed on the command line is
always scanned, even if its own name is in the list.

Round 4 adds `.gitignore` rules on top of this list; see "R5 (changed in
Round 4)" below. The list above still applies unchanged.

### R6 — Clear error for a missing or inaccessible folder

The program prints a one-line message starting with `Error:` to **stderr** and
exits with status code **1** when:

- the path does not exist → `Error: folder not found: <path>`
- the path exists but is not a directory → `Error: not a folder: <path>`
- the folder cannot be read (permission denied) → `Error: cannot access folder: <path>`

Nothing is printed to stdout in these cases. Calling the program with no
argument or too many arguments prints a usage message and exits with status 2
(standard `argparse` behaviour).

On success the exit status is 0.

### R7 — Warn about inaccessible subfolders and keep scanning (Round 2)

R6 covers the folder given on the command line. R7 covers folders **inside** it.

- A subfolder "cannot be accessed" when listing its contents fails (e.g.
  permission denied, or it disappears during the scan).
- For each such folder, one line is printed to **stderr**:
  `Warning: cannot access folder: <relative path>`, where the path is relative
  to the scanned folder and `/`-separated, like file paths in the report.
- Warnings are printed in sorted order by path, before the report is written
  to stdout.
- Scanning continues with every other folder. Files that were found are listed
  and counted as usual; nothing inside the inaccessible folder is counted.
- The summary ends with the `Incomplete:` line described in R4.
- The exit status stays **0**: the scan itself succeeded, with a known gap.
- Folders that are skipped by R5 are never entered, so they never produce a
  warning. Only the inaccessible folder itself is reported, not its contents
  (which are unknown).
- A single unreadable *file* is still handled by R3 (`(unreadable)` row), not
  by R7.

### R8 — Count each real Python file only once (Round 2)

- Two scanned paths are the **same file** when they resolve to the same
  device and inode (`os.stat`, which follows symlinks). This merges several
  symlinks to one file, a symlink plus the file itself, and hard links.
- Each real file appears on exactly one row and is counted once in the totals.
- The row shows:
  1. the first (in sorted order) path to it that is **not** a symlink, if any
     — i.e. the real file when it lives inside the scanned folder;
  2. otherwise the first symlink path in sorted order.
- A symlinked `.py` file whose target lies **outside** the scanned folder is
  scanned and listed under the symlink's path (once, however many links point
  to it).
- A **broken** symlink (target missing, or a symlink loop) is listed with 0 for
  every count and the marker `(unreadable)`, as in R3. Broken links are never
  merged with each other.
- Directory symlinks are still not followed (R1).

### R9 — `--top N`: show only the N largest files (Round 3)

- `--top N` limits the per-file table to the N files with the most lines of
  code (R2 LOC), ranked from highest to lowest.
- Files with equal LOC are ordered by relative path (the R2 order), so output
  is deterministic. Exactly `min(N, total files)` rows are shown; ties at the
  cut-off are not extended.
- N must be a whole number ≥ 1. `0`, negative numbers and non-numbers are
  rejected with an `argparse` usage error on stderr and exit status **2**,
  like other invalid arguments. Nothing is scanned in that case.
- If N is larger than the number of files, every file is shown, ranked by LOC.
- Files marked `(parse error)` or `(unreadable)` take part in the ranking with
  the LOC shown on their row (0 for unreadable files); their marker is kept.
- When `--top` is given and at least one file was found, the first line of
  stdout is:
  `Showing the K largest of M files (ranked by lines of code).`
  where K = `min(N, M)` and M = number of files scanned, followed by a blank
  line and then the table.
- The **summary is unchanged**: it counts every scanned file, not just the
  rows shown (R4). The R7 `Incomplete:` line and warnings also still appear.
- If no Python files are found, output is the same as without `--top`
  (`No Python files found.` and an all-zero summary; no `Showing` line).
- Without `--top`, the output is exactly as before (all files, sorted by path).

### R5 (changed in Round 4) — Also follow `.gitignore` rules

RepoLens still skips the default directories listed in R5. In addition, it
leaves out files and folders that the scanned folder's `.gitignore` files
ignore.

**Which `.gitignore` files are read**

- Every file named exactly `.gitignore` in the scanned folder or in any
  subfolder that is scanned. This applies whether or not the folder is a git
  repository; a `.git` folder is not needed.
- `.gitignore` files **outside** the scanned folder (in parent folders),
  `.git/info/exclude` and the user's global excludes file are **not** read.
  Output depends only on what is inside `<path>`.
- A `.gitignore` inside a folder that is skipped (default list or ignored) is
  never read.

**Which paths a `.gitignore` applies to**

- A `.gitignore` in folder `D` applies to every file and folder below `D`.
  Its patterns are matched against the path relative to `D`.
- Rules from all applicable `.gitignore` files are checked together. The
  **last matching rule wins**, where rules from a deeper `.gitignore` come
  after rules from a shallower one, and within one file later lines come after
  earlier ones. If no rule matches, the path is not ignored.
- An ignored **folder** is not entered: nothing inside it is scanned, its own
  `.gitignore` is not read, and no R7 warning is printed for it. As in git, a
  `!` rule cannot bring back a file whose parent folder is ignored.
- An ignored **`.py` file** is not listed and not counted in the summary.
- The scanned folder itself is never ignored.
- The default directories of R5 are **always** skipped, even if a
  `.gitignore` re-includes them (e.g. `!venv/`). `.gitignore` can only add to
  what is skipped.

**Pattern syntax** (git's `.gitignore` rules, implemented with the standard
library only; git itself is not needed):

- Blank lines match nothing. Lines starting with `#` are comments; `\#` at
  the start matches a literal `#`.
- Trailing spaces are removed unless escaped with `\`. A trailing `\r`
  (Windows line ending) is removed.
- A leading `!` negates the pattern: a matching path is **not** ignored.
  `\!` at the start matches a literal `!`.
- A trailing `/` makes the pattern match **folders only** (the `/` is not
  part of the pattern).
- If the pattern (without a trailing `/`) contains a `/` at the start or in
  the middle, it is **anchored**: it matches the path relative to the
  `.gitignore`'s folder. A leading `/` is removed. Otherwise the pattern
  matches the **name** of a file or folder at any depth below that folder.
- `*` matches any run of characters except `/`; `?` matches one character
  except `/`; `[...]` matches one character from the set (ranges like `a-z`,
  and `[!...]` / `[^...]` for "not in set"); it never matches `/`.
  A `[` without a closing `]` makes the whole pattern match nothing
  (as in git).
- `**`: a leading `**/` matches in every folder; a trailing `/**` matches
  everything inside; `/**/` matches zero or more folders. Any other `**`
  acts like `*`.
- `\` before any other character matches that character literally.
- Matching is case-sensitive on every platform.

**Other rules**

- A `.py` symlink is matched by its own path (where the link is), not by its
  target's path. If a file is ignored under one path but reachable under
  another path that is not ignored (a symlink or hard link), it is counted
  once under the path that is not ignored (R8).
- If a `.gitignore` exists but cannot be read (e.g. permission denied), one
  line is printed to **stderr**:
  `Warning: cannot read .gitignore: <relative path>` (relative to the scanned
  folder, `/`-separated, sorted with other such warnings, printed after the R7
  folder warnings). The scan continues as if that file were empty. The exit
  status stays 0 and no `Incomplete:` line is added (no folder was missed).
- Output format is unchanged: ignored files simply do not appear, like files
  in a default-skipped folder. There is no count of ignored files and no
  option to turn `.gitignore` handling off.

## Output format (example)

```
File                         Lines  Functions  Classes
---------------------------  -----  ---------  -------
main.py                         12          2        0
pkg/models.py                   30          5        2
pkg/broken.py                    4          0        0  (parse error)

Summary
  Files scanned:  3
  Lines of code:  46
  Functions:      7
  Classes:        2
```

Column widths adapt to the longest path.

With an inaccessible subfolder `pkg/locked` (R7), stderr gets
`Warning: cannot access folder: pkg/locked` and the summary on stdout ends with:

```
  Classes:        2
  Incomplete:     1 folder(s) could not be accessed (see warnings)
```

With `--top 2` on the same folder:

```
Showing the 2 largest of 3 files (ranked by lines of code).

File           Lines  Functions  Classes
-------------  -----  ---------  -------
pkg/models.py     30          5        2
main.py           12          2        0

Summary
  Files scanned:  3
  Lines of code:  46
  Functions:      7
  Classes:        2
```

## Constraints

- Python 3.9+, standard library only at runtime; pytest for tests.
