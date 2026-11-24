"""Find Python files under a folder and measure each one (R1, R2, R3, R5)."""

import ast
import io
import os
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from repolens.gitignore import Rule, is_ignored, parse_gitignore

# R5: directory names that are never descended into, whatever .gitignore says.
SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "node_modules",
    }
)

# Token types that do not make a line count as code.
_NON_CODE_TOKENS = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
)


@dataclass
class FileStats:
    path: str  # relative to the scanned folder, '/'-separated
    loc: int
    functions: int
    classes: int
    note: Optional[str] = None  # e.g. "parse error"


@dataclass
class Discovery:
    files: List[Path]  # sorted by relative path
    inaccessible_dirs: List[str]  # relative, '/'-separated, sorted (R7)
    # .gitignore files that exist but could not be read (R5, Round 4)
    unreadable_gitignores: List[str] = field(default_factory=list)
    # .gitignore entries that are symlinks, skipped unread (R11, Round 6)
    symlinked_gitignores: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    files: List[FileStats]
    inaccessible_dirs: List[str]
    unreadable_gitignores: List[str] = field(default_factory=list)
    symlinked_gitignores: List[str] = field(default_factory=list)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def discover(root: Path) -> Discovery:
    """Walk root for .py files (R1), skipping SKIP_DIRS and paths ignored by
    .gitignore files inside root (R5).

    Subfolders that cannot be listed are recorded instead of being silently
    dropped (R7), and so are .gitignore files that cannot be read. A
    .gitignore that is a symlink is never followed (R11): it is recorded and
    its rules are not used, as git 2.32+ does.
    """
    found = []
    inaccessible = []
    unreadable_gitignores = []  # type: List[str]
    symlinked_gitignores = []  # type: List[str]
    # Rules that apply inside each visited folder: its parents' rules, then
    # its own .gitignore's, so the last matching rule is the deepest one.
    rules_for = {}  # type: Dict[str, List[Rule]]

    def on_error(err: OSError) -> None:
        # os.walk calls this when listing a directory fails. The root itself
        # is checked by the CLI before scanning (R6), but record it anyway
        # rather than lose the information.
        if err.filename is None:
            return
        failed = Path(err.filename)
        inaccessible.append(_rel(failed, root) if failed != root else ".")

    for dirpath, dirnames, filenames in os.walk(
        root, onerror=on_error, followlinks=False
    ):
        here = Path(dirpath)
        rel_dir = _rel(here, root) if here != root else ""
        parent = rel_dir.rsplit("/", 1)[0] if "/" in rel_dir else ""
        rules = list(rules_for.get(parent, [])) if rel_dir else []
        gitignore = here / ".gitignore"
        # R11: a symlink named .gitignore may sit in filenames (file target,
        # broken link, loop) or in dirnames (folder target); skip it in both.
        if (".gitignore" in filenames or ".gitignore" in dirnames) and (
            gitignore.is_symlink()
        ):
            symlinked_gitignores.append(_join(rel_dir, ".gitignore"))
        elif ".gitignore" in filenames:
            try:
                text = gitignore.read_text(
                    encoding="utf-8", errors="surrogateescape"
                )
            except OSError:
                unreadable_gitignores.append(_join(rel_dir, ".gitignore"))
            else:
                rules.extend(parse_gitignore(text, rel_dir))
        rules_for[rel_dir] = rules

        # Prune in place so os.walk never enters skipped or ignored folders.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIRS and not is_ignored(rules, _join(rel_dir, d), True)
        ]
        for name in filenames:
            if name.endswith(".py") and not is_ignored(
                rules, _join(rel_dir, name), False
            ):
                found.append(here / name)
    return Discovery(
        files=sorted(_one_path_per_file(found), key=lambda p: _rel(p, root)),
        inaccessible_dirs=sorted(inaccessible),
        unreadable_gitignores=sorted(unreadable_gitignores),
        symlinked_gitignores=sorted(symlinked_gitignores),
    )


def _join(rel_dir: str, name: str) -> str:
    return rel_dir + "/" + name if rel_dir else name


def _one_path_per_file(paths: List[Path]) -> List[Path]:
    """Keep one path per real file (R8).

    Paths are the same file when os.stat (which follows symlinks) gives the
    same (device, inode); see docs/decisions/0002. From each group, keep the
    first non-symlink path in sorted order, else the first symlink. Paths
    that cannot be stat'ed (broken links, loops) are kept as-is, so that
    analyze_file reports them as unreadable.
    """
    groups = {}  # type: Dict[Union[Tuple[int, int], str], List[Path]]
    for path in paths:
        try:
            st = path.stat()
            key = (st.st_dev, st.st_ino)  # type: Union[Tuple[int, int], str]
        except OSError:
            key = str(path)
        groups.setdefault(key, []).append(path)
    return [
        min(group, key=lambda p: (p.is_symlink(), p.as_posix()))
        for group in groups.values()
    ]


def find_python_files(root: Path) -> List[Path]:
    """Return every .py file under root (R1), minus skipped and ignored ones (R5), sorted."""
    return discover(root).files


def count_loc(source: bytes) -> int:
    """Count lines holding at least one non-comment token (R2)."""
    code_lines = set()
    try:
        for tok in tokenize.tokenize(io.BytesIO(source).readline):
            if tok.type in _NON_CODE_TOKENS:
                continue
            # Multi-line tokens (e.g. docstrings) cover every line they span.
            code_lines.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError, UnicodeDecodeError, ValueError):
        return _count_loc_fallback(source)
    return len(code_lines)


def _count_loc_fallback(source: bytes) -> int:
    """Simple line rule for files the tokenizer rejects."""
    text = source.decode("utf-8", errors="replace")
    return sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def count_definitions(source: bytes) -> Tuple[int, int]:
    """Return (functions, classes) at any nesting level (R3).

    Raises SyntaxError or ValueError if the source cannot be parsed.
    """
    tree = ast.parse(source)
    functions = 0
    classes = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1
    return functions, classes


def analyze_file(path: Path, root: Path) -> FileStats:
    rel = path.relative_to(root).as_posix()
    try:
        source = path.read_bytes()
    except OSError:
        return FileStats(rel, 0, 0, 0, note="unreadable")

    loc = count_loc(source)
    try:
        functions, classes = count_definitions(source)
    except (SyntaxError, ValueError, UnicodeDecodeError, RecursionError):
        return FileStats(rel, loc, 0, 0, note="parse error")
    return FileStats(rel, loc, functions, classes)


def scan(root: Path) -> ScanResult:
    found = discover(root)
    return ScanResult(
        files=[analyze_file(p, root) for p in found.files],
        inaccessible_dirs=found.inaccessible_dirs,
        unreadable_gitignores=found.unreadable_gitignores,
        symlinked_gitignores=found.symlinked_gitignores,
    )
