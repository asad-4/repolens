import os
import sys

import pytest


def test_r6_missing_folder_gives_clear_error(run_cli, tmp_path):
    missing = tmp_path / "does_not_exist"
    code, out, err = run_cli(missing)
    assert code == 1
    assert out == ""
    assert err.strip() == "Error: folder not found: {}".format(missing)


def test_r6_file_instead_of_folder_gives_clear_error(run_cli, tmp_path):
    a_file = tmp_path / "file.py"
    a_file.write_text("x = 1\n")
    code, out, err = run_cli(a_file)
    assert code == 1
    assert out == ""
    assert err.strip() == "Error: not a folder: {}".format(a_file)


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)
def test_r6_unreadable_folder_gives_clear_error(run_cli, tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        code, out, err = run_cli(locked)
    finally:
        locked.chmod(0o755)
    assert code == 1
    assert out == ""
    assert err.strip() == "Error: cannot access folder: {}".format(locked)


def test_r6_success_exits_zero(run_cli, fixtures_dir):
    code, _, err = run_cli(fixtures_dir / "basic")
    assert code == 0
    assert err == ""
