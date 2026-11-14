# repolens — Specification (Round 1)

repolens is a command-line tool that gives a quick overview of a Python codebase:
which files exist, how big they are, and how many functions and classes they hold.

Source of requirements: `problem.md` (R1–R6). This document makes each requirement
precise enough to test.

## Usage

```
python -m repolens <path>
```

Exactly one positional argument: the folder to scan.

## Requirements

### R1 — Accept a folder and scan Python files recursively

- The folder path is given as the single command-line argument.
- Every file whose name ends in `.py` inside that folder, at any depth, is scanned.
- Files with other extensions (`.txt`, `.pyc`, `.pyi`, …) are ignored.
- Symbolic links to directories are not followed (avoids infinite loops).

### R2 — Per-file relative path and lines of code

- For each scanned file, the output shows its path relative to the given folder,
  using `/` as the separator on every platform.
- Files are listed in sorted order by relative path, so output is deterministic.
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

### R5 — Skip unnecessary directories

Directories with the following names are skipped at any depth, together with
everything inside them:

`.git`, `.hg`, `.svn`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`,
`.mypy_cache`, `.tox`, `node_modules`

Matching is by exact directory name. The folder passed on the command line is
always scanned, even if its own name is in the list.

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

## Constraints

- Python 3.9+, standard library only at runtime; pytest for tests.
