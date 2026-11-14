# 0002 — Identify "the same file" by device and inode, not by resolved path

- Status: accepted
- Date: 2026-11-14
- Requirements: R8 (and R3 for broken links)

## Decision (Y-statement)

In the context of **counting each real Python file only once even when several
symlinks point to it (R8)**,
facing **the need to decide when two paths found by the folder walk are "the
same actual file"**,
we decided for **grouping paths by the `(st_dev, st_ino)` pair returned by
`os.stat`, which follows symlinks, and keeping one path per group (the first
non-symlink path, else the first symlink, in sorted order)**,
and neglected **comparing `os.path.realpath()` / `Path.resolve()` strings**,
**counting only regular files and ignoring every symlink**, and **comparing
file contents (hashing)**,
to achieve **totals where every file on disk is counted exactly once, however
it is reached — one symlink, many symlinks, relative or absolute links, chains
of links, or hard links — with no string normalisation edge cases**,
accepting that **hard links are merged too (the user agreed this is wanted),
that one extra `stat` call is made per file, and that paths which cannot be
stat'ed (broken links, link loops) are never merged and are reported as
`(unreadable)`**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **`(st_dev, st_ino)` from `os.stat` (chosen)** | Asks the file system directly which file a path is. Handles chains of links, relative links, links through symlinked parent folders and hard links. Works on Python 3.9 standard library, including Windows (NTFS file IDs). | One `stat` per file. Merges hard links (wanted here). Two paths on network file systems with unstable inode numbers could, in rare cases, be misjudged. |
| `os.path.realpath()` string comparison | Easy to read; gives a "real path" to display. | Case-insensitive file systems (default on macOS) can produce different strings for the same file; `realpath` on 3.9 does not raise on loops and silently returns a path, so broken links need separate checks; hard links stay double-counted. |
| Ignore every symlink, count only regular files | Simplest; no duplicates possible. | Loses files whose only path in the folder is a symlink to somewhere outside it, which the user asked to count once. Silently changes R1 behaviour. |
| Hash file contents | Also catches copy-pasted duplicates. | Wrong: two different files with identical contents (e.g. empty `__init__.py`) are separate files and must both be counted. Reads every file twice. |

## Consequences

- `find_python_files()` and `scan()` return at most one path per real file.
  The shown path is the real one when it lives in the scanned folder, which is
  the path a user would open.
- Two separate files with the same content are both counted (tested).
- Broken links and link loops raise `OSError` on `stat`, are kept as separate
  entries and are listed with zeros and `(unreadable)`, consistent with R3.
