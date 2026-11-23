"""Command-line entry point: python -m repolens <path> [--top N] (R1, R6, R9)."""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from repolens.report import format_report
from repolens.scanner import scan


def _check_folder(path: Path) -> Optional[str]:
    """Return an error message if path is not a readable folder (R6)."""
    if not path.exists():
        return "Error: folder not found: {}".format(path)
    if not path.is_dir():
        return "Error: not a folder: {}".format(path)
    try:
        os.listdir(path)
    except OSError:
        return "Error: cannot access folder: {}".format(path)
    return None


def _positive_int(text: str) -> int:
    """argparse type for --top: a whole number of 1 or more (R9)."""
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(
            "must be a whole number of 1 or more, got {!r}".format(text)
        )
    return value


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repolens",
        description="Summarise the Python files in a folder.",
    )
    parser.add_argument("path", help="folder to scan")
    parser.add_argument(
        "--top",
        type=_positive_int,
        metavar="N",
        help="show only the N files with the most lines of code "
        "(the summary still counts every file)",
    )
    args = parser.parse_args(argv)

    root = Path(args.path)
    error = _check_folder(root)
    if error:
        print(error, file=sys.stderr)
        return 1

    result = scan(root)
    # R7: warn about each inaccessible subfolder, then report what was found.
    for rel in result.inaccessible_dirs:
        print("Warning: cannot access folder: {}".format(rel), file=sys.stderr)
    # R5: an unreadable .gitignore is treated as empty, but say so.
    for rel in result.unreadable_gitignores:
        print("Warning: cannot read .gitignore: {}".format(rel), file=sys.stderr)
    print(format_report(result.files, len(result.inaccessible_dirs), args.top))
    return 0
