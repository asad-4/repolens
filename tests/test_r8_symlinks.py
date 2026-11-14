"""R8: each real Python file is counted once, however many links point to it.

Trees are built in tmp_path because symlinks in tests/fixtures/ would be
fragile across checkouts and platforms."""

import os
import sys

import pytest

from conftest import row_for
from repolens.scanner import find_python_files

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="creating symlinks needs privileges on Windows"
)

TWO_FUNCS = "def a():\n    pass\n\n\ndef b():\n    pass\n"  # 4 LOC, 2 functions


def make_file(path, text="x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def rel_names(root):
    return [p.relative_to(root).as_posix() for p in find_python_files(root)]


def test_r8_symlink_and_real_file_counted_once(run_cli, tmp_path):
    make_file(tmp_path / "real" / "r.py", TWO_FUNCS)
    os.symlink(tmp_path / "real" / "r.py", tmp_path / "link.py")
    _, out, _ = run_cli(tmp_path)
    assert row_for(out, "real/r.py") == (4, 2, 0)
    assert "link.py" not in out
    assert "Files scanned:  1" in out
    assert "Lines of code:  4" in out
    assert "Functions:      2" in out


def test_r8_many_symlinks_to_one_file_counted_once(run_cli, tmp_path):
    make_file(tmp_path / "real.py", TWO_FUNCS)
    for name in ["a.py", "b.py", "sub/c.py"]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(tmp_path / "real.py", tmp_path / name)
    assert rel_names(tmp_path) == ["real.py"]
    _, out, _ = run_cli(tmp_path)
    assert "Files scanned:  1" in out
    assert "Functions:      2" in out


def test_r8_real_path_shown_even_when_link_sorts_first(tmp_path):
    make_file(tmp_path / "zzz" / "real.py")
    os.symlink(tmp_path / "zzz" / "real.py", tmp_path / "aaa.py")
    assert rel_names(tmp_path) == ["zzz/real.py"]


def test_r8_relative_symlink_is_merged_too(tmp_path):
    make_file(tmp_path / "pkg" / "real.py")
    os.symlink(os.path.join("pkg", "real.py"), tmp_path / "alias.py")
    assert rel_names(tmp_path) == ["pkg/real.py"]


def test_r8_link_to_outside_file_counted_once_under_first_link(run_cli, tmp_path):
    outside = tmp_path / "outside.py"
    make_file(outside, TWO_FUNCS)
    root = tmp_path / "project"
    root.mkdir()
    os.symlink(outside, root / "b_link.py")
    os.symlink(outside, root / "a_link.py")
    assert rel_names(root) == ["a_link.py"]
    _, out, _ = run_cli(root)
    assert row_for(out, "a_link.py") == (4, 2, 0)
    assert "Files scanned:  1" in out


def test_r8_hard_links_counted_once(tmp_path):
    make_file(tmp_path / "a.py")
    os.link(tmp_path / "a.py", tmp_path / "b.py")
    assert rel_names(tmp_path) == ["a.py"]


def test_r8_different_files_with_same_content_both_counted(tmp_path):
    make_file(tmp_path / "one.py", TWO_FUNCS)
    make_file(tmp_path / "two.py", TWO_FUNCS)
    assert rel_names(tmp_path) == ["one.py", "two.py"]


def test_r8_broken_symlink_listed_as_unreadable(run_cli, tmp_path):
    make_file(tmp_path / "ok.py")
    os.symlink(tmp_path / "missing.py", tmp_path / "dangling.py")
    os.symlink(tmp_path / "gone.py", tmp_path / "dangling2.py")
    code, out, _ = run_cli(tmp_path)
    assert code == 0
    for name in ["dangling.py", "dangling2.py"]:
        line = next(l for l in out.splitlines() if l.startswith(name + " "))
        assert line.endswith("(unreadable)")
        assert row_for(out, name) == (0, 0, 0)
    assert "Files scanned:  3" in out


def test_r8_symlink_loop_listed_as_unreadable(run_cli, tmp_path):
    os.symlink(tmp_path / "b.py", tmp_path / "a.py")
    os.symlink(tmp_path / "a.py", tmp_path / "b.py")
    _, out, _ = run_cli(tmp_path)
    assert row_for(out, "a.py") == (0, 0, 0)
    assert row_for(out, "b.py") == (0, 0, 0)
    assert "(unreadable)" in out


def test_r8_r1_directory_symlinks_still_not_followed(tmp_path):
    make_file(tmp_path / "pkg" / "mod.py")
    os.symlink(tmp_path / "pkg", tmp_path / "pkg_alias", target_is_directory=True)
    os.symlink(tmp_path, tmp_path / "pkg" / "loop", target_is_directory=True)
    assert rel_names(tmp_path) == ["pkg/mod.py"]
