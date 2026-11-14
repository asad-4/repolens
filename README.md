# repolens

repolens gives you a quick overview of an unfamiliar Python codebase. Point it at a
folder and it lists every Python file (including those in subfolders) with:

- its path relative to the folder,
- lines of code (blank lines and comments excluded),
- the number of functions (including `async def` and methods) and classes,

followed by a summary of totals. Folders like `.git`, `.venv`, `venv` and
`__pycache__` are skipped automatically. Full behaviour is in [spec.md](spec.md).

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
python -m repolens <path>
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

If the folder does not exist, is not a folder, or cannot be read, repolens prints
an `Error:` message to stderr and exits with status 1.

If a folder *inside* it cannot be read, repolens prints
`Warning: cannot access folder: <path>` to stderr, scans everything else, and
adds an `Incomplete:` line to the summary so you know the totals are partial.

A file reached through several symlinks (or hard links) is listed and counted
only once, under its real path when that is inside the folder.

## Test

```
pytest
```

Run from the repository root. Tests live in `tests/`, one file per requirement,
with sample projects in `tests/fixtures/`.
