"""R7: an inaccessible subfolder produces a warning and the scan continues.

Trees are built in tmp_path because permission bits cannot be committed
reliably to git."""

import os
import sys

import pytest

from conftest import row_for

needs_permissions = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)


def make_file(path, text="x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def locked_dirs():
    """Lock folders with chmod 0 and always unlock them afterwards."""
    locked = []

    def _lock(path):
        path.chmod(0)
        locked.append(path)

    yield _lock
    for path in locked:
        path.chmod(0o755)


@needs_permissions
def test_r7_warns_with_relative_path_on_stderr(run_cli, tmp_path, locked_dirs):
    make_file(tmp_path / "keep.py")
    make_file(tmp_path / "pkg" / "locked" / "hidden.py")
    locked_dirs(tmp_path / "pkg" / "locked")
    code, out, err = run_cli(tmp_path)
    assert err.splitlines() == ["Warning: cannot access folder: pkg/locked"]
    assert "Warning" not in out


@needs_permissions
def test_r7_scan_continues_after_inaccessible_folder(run_cli, tmp_path, locked_dirs):
    make_file(tmp_path / "a" / "first.py", "def f():\n    pass\n")
    make_file(tmp_path / "b_locked" / "hidden.py")
    make_file(tmp_path / "c" / "last.py", "class C:\n    pass\n")
    locked_dirs(tmp_path / "b_locked")
    code, out, _ = run_cli(tmp_path)
    assert code == 0
    assert row_for(out, "a/first.py") == (2, 1, 0)
    assert row_for(out, "c/last.py") == (2, 0, 1)
    assert "hidden.py" not in out
    assert "Files scanned:  2" in out


@needs_permissions
def test_r7_summary_says_results_are_incomplete(run_cli, tmp_path, locked_dirs):
    make_file(tmp_path / "keep.py")
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    locked_dirs(tmp_path / "one")
    locked_dirs(tmp_path / "two")
    _, out, err = run_cli(tmp_path)
    assert out.rstrip().splitlines()[-1] == (
        "  Incomplete:     2 folder(s) could not be accessed (see warnings)"
    )
    assert err.splitlines() == [
        "Warning: cannot access folder: one",
        "Warning: cannot access folder: two",
    ]


@needs_permissions
def test_r7_warnings_are_sorted_by_path(run_cli, tmp_path, locked_dirs):
    for name in ["zeta", "alpha", "mid/inner"]:
        (tmp_path / name).mkdir(parents=True)
    for name in ["zeta", "alpha", "mid/inner"]:
        locked_dirs(tmp_path / name)
    _, _, err = run_cli(tmp_path)
    assert err.splitlines() == [
        "Warning: cannot access folder: alpha",
        "Warning: cannot access folder: mid/inner",
        "Warning: cannot access folder: zeta",
    ]


@needs_permissions
def test_r7_no_python_files_still_warns(run_cli, tmp_path, locked_dirs):
    (tmp_path / "locked").mkdir()
    locked_dirs(tmp_path / "locked")
    code, out, err = run_cli(tmp_path)
    assert code == 0
    assert "No Python files found." in out
    assert "Incomplete:     1 folder(s)" in out
    assert "Warning: cannot access folder: locked" in err


@needs_permissions
def test_r7_skipped_folders_never_warn(run_cli, tmp_path, locked_dirs):
    make_file(tmp_path / "keep.py")
    (tmp_path / ".venv").mkdir()
    locked_dirs(tmp_path / ".venv")
    code, out, err = run_cli(tmp_path)
    assert err == ""
    assert "Incomplete" not in out


def test_r7_no_warning_or_incomplete_line_when_all_readable(run_cli, fixtures_dir):
    code, out, err = run_cli(fixtures_dir / "basic")
    assert code == 0
    assert err == ""
    assert "Incomplete" not in out
