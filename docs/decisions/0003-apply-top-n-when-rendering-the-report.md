# 0003 — Apply `--top N` when rendering the report, not in the scanner

- Status: accepted
- Date: 2026-11-22
- Requirements: R9 (and R4, R7)

## Decision (Y-statement)

In the context of **adding `--top N` to show only the N largest Python files
(R9)**,
facing **the requirement that the summary must still count every scanned file,
while the table shows only N rows ranked by lines of code**,
we decided for **scanning every file exactly as before and choosing the N rows
only inside `format_report()` (a `largest_files(stats, n)` helper sorted by
`(-loc, path)`), so the table and the summary are computed from the same full
list**,
and neglected **cutting the list in `scan()` / the CLI and passing separately
computed totals to the report**, **keeping only N files while scanning (a
bounded heap)**, and **marking hidden rows and filtering them at print time**,
to achieve **a summary that cannot drift from the full scan (it is the same
code path with the same input as without `--top`), an unchanged
`scan()`/`ScanResult` API, and a ranking that is one small, testable
function**,
accepting that **every file's stats are kept in memory even when only a few
rows are printed, and that `format_report()` now takes a third parameter**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Select rows in `format_report()` (chosen)** | Summary code is untouched, so the totals stay identical to a run without `--top` (tested). Scanner and R7/R8 logic unchanged. Ranking is a pure function. | All `FileStats` held in memory (a few numbers per file, which is small even for large repositories). |
| Cut the list in the CLI and pass precomputed totals to the report | Report only sees what it prints. | Two sources of truth for totals; `format_report()` would need a new totals parameter, and the R4 summary code would be duplicated or split. Easy to sum the cut list by mistake, which is exactly what R9 forbids. |
| Keep only the N largest while scanning (`heapq`) | Lowest memory use. | Every file still has to be read and counted for the summary, so no time is saved; mixes presentation into the scanner and changes `scan()`'s return type again (it already changed in Round 2). |
| Mark rows hidden and skip them when printing | Keeps one list. | Adds a display-only field to `FileStats`, a data class that describes a file, not how it is shown. |

## Consequences

- `python -m repolens <path>` without `--top` prints the same output as before
  (`top=None` leaves rows in path order); the earlier tests pass unchanged.
- The `Showing the K largest of M files` line is built in the same place, from
  the full list (M) and the shown list (K), so it always agrees with the
  summary's `Files scanned` count.
- Ties are ordered by path because the sort key is `(-loc, path)`.
