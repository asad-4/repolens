"""Command-line entry point: python -m repolens <path> (R1, R6)."""

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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repolens",
        description="Summarise the Python files in a folder.",
    )
    parser.add_argument("path", help="folder to scan")
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
    print(format_report(result.files, len(result.inaccessible_dirs)))
    return 0
