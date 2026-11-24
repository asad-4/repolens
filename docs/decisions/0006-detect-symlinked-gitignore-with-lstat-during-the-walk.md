# 0006 — Detect a symlinked `.gitignore` with an `lstat` check during the walk, for every kind of link target

- Status: accepted
- Date: 2026-11-23
- Requirements: R11 (and R5 changed in Round 4, R10)

## Decision (Y-statement)

In the context of **skipping a `.gitignore` that is a symbolic link without
following it or applying its rules, so RepoLens behaves like git (R11)**,
facing **the "standard library only, Python 3.9, must also run on Windows"
rule, a walk (`os.walk`, `followlinks=False`) that puts a link in `filenames`
or in `dirnames` depending on its target, broken links that today produce a
`cannot read .gitignore` warning, and the user's choice to warn about each
skipped link on stderr and in the JSON**,
we decided for **checking `Path.is_symlink()` (an `lstat`, which never
follows the link) on `<folder>/.gitignore` whenever that name appears in
`filenames` or `dirnames`, recording the path in a new
`symlinked_gitignores` list and only otherwise reading the file as before**,
and neglected **opening the file with `os.O_NOFOLLOW` and treating `ELOOP`
as "is a symlink"**, **resolving the path and skipping only links whose
target lies outside the scanned folder**, and **checking only `filenames`**,
to achieve **one rule that covers every kind of link (to a file inside or
outside the folder, to a folder, broken, or a loop), never opens the target,
works the same on every platform, and keeps the R5 reading code and the
unreadable-`.gitignore` path unchanged for regular files**,
accepting that **there is a small race (the entry could be replaced by a
link between the `lstat` and the read), that a broken `.gitignore` link is
now reported as a symlink rather than as unreadable, and that the check costs
one extra `lstat` per folder that has a `.gitignore`**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **`is_symlink()` before reading, on `filenames` and `dirnames` (chosen)** | Standard library, same on all platforms. The target is never touched. Easy to read and test; a clean "is it a link?" answer for every case, including links to folders. | Check-then-read race. Needs care to look in both lists. |
| `os.open(..., O_RDONLY \| O_NOFOLLOW)`, `ELOOP` means "symlink" (what git does) | No race: the kernel refuses to follow the link. | `O_NOFOLLOW` does not exist on Windows; needs a fallback anyway. `ELOOP` also means a real link loop elsewhere in the path, and some systems return other codes (`EMLINK` on FreeBSD), so the error would have to be mapped back to "symlink". Links to folders never reach the open. |
| Skip only links that point **outside** the scanned folder | Keeps rules from a link to another file in the repo. | Not what R11 or git says ("without following the link"). Must resolve the link to decide, i.e. follow it. |
| Check only `filenames` | One list to check. | A `.gitignore` link to a folder lands in `dirnames` and would get no warning, unlike git, which warns for any symlinked `.gitignore`. |

## Consequences

- `Discovery` and `ScanResult` gained `symlinked_gitignores` (default empty,
  so older callers still work), and `format_json()` gained a last optional
  argument with the same name.
- stderr order is: inaccessible folders, unreadable `.gitignore` files, then
  symlinked `.gitignore` files, each sorted by path.
- A link inside a skipped or ignored folder is never seen, so it gets no
  warning, the same as other `.gitignore` files there.
- If the race ever matters, the read could switch to `O_NOFOLLOW` where the
  platform has it, keeping the `lstat` check for Windows and folder links.
