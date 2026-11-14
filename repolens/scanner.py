"""Find Python files under a folder and measure each one (R1, R2, R3, R5)."""

import ast
import io
import os
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# R5: directory names that are never descended into.
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


def find_python_files(root: Path) -> List[Path]:
    """Return every .py file under root (R1), skipping SKIP_DIRS (R5), sorted."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune in place so os.walk never enters skipped directories.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                found.append(Path(dirpath) / name)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


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


def scan(root: Path) -> List[FileStats]:
    return [analyze_file(p, root) for p in find_python_files(root)]
