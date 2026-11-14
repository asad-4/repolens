"""R5 tests build their trees in tmp_path rather than tests/fixtures/,
because .git, .venv and __pycache__ folders cannot be committed to this repo
(.gitignore excludes them, and git refuses nested .git directories)."""

import pytest

from repolens.scanner import SKIP_DIRS, find_python_files


def make_file(path, text="x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def rel_names(root):
    return [p.relative_to(root).as_posix() for p in find_python_files(root)]


@pytest.mark.parametrize("skipped", [".git", ".venv", "venv", "__pycache__"])
def test_r5_skips_required_directories(tmp_path, skipped):
    make_file(tmp_path / "keep.py")
    make_file(tmp_path / skipped / "hidden.py")
    assert rel_names(tmp_path) == ["keep.py"]


def test_r5_skips_directories_at_any_depth(tmp_path):
    make_file(tmp_path / "app" / "keep.py")
    make_file(tmp_path / "app" / "venv" / "lib" / "site.py")
    make_file(tmp_path / "app" / "inner" / "__pycache__" / "cached.py")
    assert rel_names(tmp_path) == ["app/keep.py"]


def test_r5_skip_list_contains_required_names():
    assert {".git", ".venv", "venv", "__pycache__"} <= SKIP_DIRS


def test_r5_only_exact_names_are_skipped(tmp_path):
    make_file(tmp_path / "venv_tools" / "tool.py")
    make_file(tmp_path / "my.git" / "thing.py")
    assert rel_names(tmp_path) == ["my.git/thing.py", "venv_tools/tool.py"]


def test_r5_root_folder_is_scanned_even_if_named_venv(tmp_path):
    root = tmp_path / "venv"
    make_file(root / "inside.py")
    assert rel_names(root) == ["inside.py"]


def test_r5_skipped_files_do_not_appear_in_output(run_cli, tmp_path):
    make_file(tmp_path / "keep.py")
    make_file(tmp_path / ".venv" / "hidden.py")
    _, out, _ = run_cli(tmp_path)
    assert "keep.py" in out
    assert "hidden.py" not in out
    assert "Files scanned:  1" in out
