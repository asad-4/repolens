import subprocess
import sys
from pathlib import Path

import pytest

from repolens.scanner import find_python_files

REPO_ROOT = Path(__file__).resolve().parent.parent


def rel_names(root):
    return [p.relative_to(root).as_posix() for p in find_python_files(root)]


def test_r1_finds_python_files_in_subfolders(fixtures_dir):
    root = fixtures_dir / "basic"
    assert rel_names(root) == [
        "main.py",
        "pkg/__init__.py",
        "pkg/models.py",
        "pkg/sub/deep.py",
    ]


def test_r1_ignores_non_python_files(fixtures_dir):
    names = rel_names(fixtures_dir / "basic")
    assert "notes.txt" not in names
    assert "stub.pyi" not in names


def test_r1_accepts_folder_path_on_command_line(fixtures_dir):
    result = subprocess.run(
        [sys.executable, "-m", "repolens", str(fixtures_dir / "basic")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "pkg/sub/deep.py" in result.stdout


def test_r1_requires_a_path_argument(run_cli):
    with pytest.raises(SystemExit) as exc:
        run_cli()
    assert exc.value.code == 2
