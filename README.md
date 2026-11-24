# repolens

repolens gives you a quick overview of an unfamiliar Python codebase. Point it at a
folder and it lists every Python file (including those in subfolders) with:

- its path relative to the folder,
- lines of code (blank lines and comments excluded),
- the number of functions (including `async def` and methods) and classes,

followed by a summary of totals. Folders like `.git`, `.venv`, `venv` and
`__pycache__` are skipped automatically, and so is anything ignored by a
`.gitignore` file inside the scanned folder (including nested `.gitignore`
files and wildcard patterns; git itself is not needed). Full behaviour is in
[spec.md](spec.md).

## Setup

Requires Python 3.9 or newer.

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

repolens itself uses only the standard library; `requirements.txt` installs
pytest for the tests.

## Run

```
python -m repolens <path> [--top N] [--format {table,json}]
```

Example:

```
$ python -m repolens tests/fixtures/basic
File             Lines  Functions  Classes
---------------  -----  ---------  -------
main.py              5          1        0
pkg/__init__.py      0          0        0
pkg/models.py        7          2        2
pkg/sub/deep.py      2          1        0

Summary
  Files scanned:  4
  Lines of code:  14
  Functions:      4
  Classes:        2
```

To see only the biggest files, add `--top N`. The table then lists the N files
with the most lines of code, largest first; the summary still covers every file:

```
$ python -m repolens tests/fixtures/basic --top 2
Showing the 2 largest of 4 files (ranked by lines of code).

File           Lines  Functions  Classes
-------------  -----  ---------  -------
pkg/models.py      7          2        2
main.py            5          1        0

Summary
  Files scanned:  4
  Lines of code:  14
  Functions:      4
  Classes:        2
```

N must be a whole number of 1 or more.

To feed the results to another program, add `--format json`. stdout then holds
one JSON object with the same files (and `--top` ranking) and the same summary
totals as the table:

```
$ python -m repolens tests/fixtures/basic --format json
{
  "files": [
    {
      "path": "main.py",
      "lines": 5,
      "functions": 1,
      "classes": 0,
      "note": null
    },
    ...
  ],
  "summary": {
    "files_scanned": 4,
    "lines_of_code": 14,
    "functions": 4,
    "classes": 2
  },
  "inaccessible_folders": [],
  "unreadable_gitignores": [],
  "top": null
}
```

`note` is `"parse error"`, `"unreadable"` or `null`. Warnings are still printed
to stderr and are also listed in `inaccessible_folders` and
`unreadable_gitignores`. `--format table` (the default) gives the normal table.

If the folder does not exist, is not a folder, or cannot be read, repolens prints
an `Error:` message to stderr and exits with status 1.

If a folder *inside* it cannot be read, repolens prints
`Warning: cannot access folder: <path>` to stderr, scans everything else, and
adds an `Incomplete:` line to the summary so you know the totals are partial.
If a `.gitignore` cannot be read, it prints
`Warning: cannot read .gitignore: <path>` and scans as if that file were empty.

A file reached through several symlinks (or hard links) is listed and counted
only once, under its real path when that is inside the folder.

## Test

```
pytest
```

Run from the repository root. Tests live in `tests/`, one file per requirement,
with sample projects in `tests/fixtures/`.
