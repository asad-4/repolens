# 0005 — Print `--format json` as one indented, ASCII-only object, built beside the table renderer

- Status: accepted
- Date: 2026-11-23
- Requirements: R10 (and R4, R7, R9)

## Decision (Y-statement)

In the context of **adding `--format json` so other programs can read the
report with the same files and summary totals as the table (R10)**,
facing **the need for the JSON and the table to always agree (including with
`--top`, where the rows are cut but the summary is not), for stdout to be
parseable by any JSON reader on any terminal, and for the output to be
stable enough to test as exact values**,
we decided for **a separate `format_json()` function in `report.py` that
picks rows with the same `largest_files()` helper as `format_report()` and
sums the summary over the full list, writing one JSON object with a fixed key
order via the standard `json` module (`indent=2`, `ensure_ascii=True`)**,
and neglected **serialising the `FileStats` dataclasses directly with
`dataclasses.asdict`**, **JSON Lines (one object per file, then a summary
line)**, **compact single-line JSON**, and **a shared "report model" that
both renderers would consume**,
to achieve **JSON that cannot drift from the table (same row selection, same
summary input; tested by comparing both outputs on every fixture), stable
public key names that do not expose internal field names, and output that is
pure ASCII and readable by people as well as programs**,
accepting that **the row/summary logic is written twice (about ten lines each
in `format_report()` and `format_json()`), that the output is larger than
compact JSON, and that non-ASCII paths appear as `\uXXXX` escapes when read
as raw text**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **`format_json()` beside `format_report()`, one object, `indent=2`, ASCII (chosen)** | Reuses `largest_files()`, so `--top` ranking is identical. Fixed key names (`lines`, `files_scanned`) chosen for readers, not tied to code. Works with `json.load`, `jq`, any language. Safe to print on terminals that are not UTF-8. | Summary sums repeated in two functions. Larger output. |
| `dataclasses.asdict(FileStats)` | Least code. | Leaks internal names (`loc`) into a public format; renaming a field later would silently break users' scripts. No place for the summary without extra wrapping anyway. |
| JSON Lines (one file per line, summary last) | Streams well for huge repositories. | Not one JSON document: `json.load` fails on it, and readers must tell file lines from the summary line. The scan already holds every file in memory (decision 0003), so streaming saves nothing. |
| Compact JSON (no indent) | Smallest output. | Hard for people to read in a terminal; programs do not care either way. |
| Shared report model used by both renderers | Sums computed once. | A new class and a refactor of `format_report()`, whose exact text is asserted by many earlier tests, for a ten-line saving. |

## Consequences

- `format_report()` and the table output are unchanged; every earlier test
  passes untouched.
- `tests/test_r10_json.py` checks, for each fixture, that the JSON paths,
  numbers and totals equal the table's, so a future change to one renderer
  that is not made to the other fails a test.
- Warnings keep going to stderr in both formats, and the JSON also lists them
  (`inaccessible_folders`, `unreadable_gitignores`), as the user chose.
- Adding a field later (e.g. per-file comment counts) means adding a key to
  `format_json()`; adding keys at the end keeps existing readers working.
