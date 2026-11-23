"""R9: --top N shows only the N largest files by lines of code; the summary
still covers every scanned file."""

import os
import sys

import pytest

from conftest import row_for

needs_permissions = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)


def make_file(path, loc):
    """Write a .py file with exactly `loc` lines of code."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join("x{} = {}\n".format(i, i) for i in range(loc)))


def table_paths(stdout):
    """Paths on the table rows, in printed order."""
    lines = stdout.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("---")) + 1
    paths = []
    for line in lines[start:]:
        if not line.strip():
            break
        paths.append(line.split()[0])
    return paths


@pytest.fixture
def sized_tree(tmp_path):
    """Five files: 10, 3, 7, 7 and 1 lines of code (two tie at 7)."""
    make_file(tmp_path / "big.py", 10)
    make_file(tmp_path / "small.py", 3)
    make_file(tmp_path / "pkg/b_mid.py", 7)
    make_file(tmp_path / "a_mid.py", 7)
    make_file(tmp_path / "tiny.py", 1)
    return tmp_path


def test_r9_shows_only_n_rows_ranked_by_loc(run_cli, sized_tree):
    code, out, err = run_cli(sized_tree, "--top", "3")
    assert code == 0
    assert err == ""
    assert table_paths(out) == ["big.py", "a_mid.py", "pkg/b_mid.py"]


def test_r9_ties_are_ordered_by_path(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "2")
    # a_mid.py and pkg/b_mid.py both have 7 LOC; only the first by path fits.
    assert table_paths(out) == ["big.py", "a_mid.py"]


def test_r9_summary_still_counts_all_files(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "1")
    assert table_paths(out) == ["big.py"]
    assert "  Files scanned:  5" in out
    assert "  Lines of code:  28" in out


def test_r9_summary_matches_run_without_top(run_cli, fixtures_dir):
    _, full, _ = run_cli(fixtures_dir / "basic")
    _, top, _ = run_cli(fixtures_dir / "basic", "--top", "2")
    summary = lambda out: out[out.index("Summary"):]
    assert summary(top) == summary(full)


def test_r9_rows_keep_their_numbers(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic", "--top", "2")
    assert table_paths(out) == ["pkg/models.py", "main.py"]
    assert row_for(out, "pkg/models.py") == (7, 2, 2)
    assert row_for(out, "main.py") == (5, 1, 0)


def test_r9_prints_showing_line_first(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "3")
    lines = out.splitlines()
    assert lines[0] == "Showing the 3 largest of 5 files (ranked by lines of code)."
    assert lines[1] == ""
    assert lines[2].startswith("File")


def test_r9_n_larger_than_file_count_shows_all(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "50")
    assert out.splitlines()[0] == (
        "Showing the 5 largest of 5 files (ranked by lines of code)."
    )
    assert table_paths(out) == [
        "big.py", "a_mid.py", "pkg/b_mid.py", "small.py", "tiny.py",
    ]


def test_r9_option_may_come_before_path(run_cli, sized_tree):
    _, out, _ = run_cli("--top", "1", sized_tree)
    assert table_paths(out) == ["big.py"]


@pytest.mark.parametrize("value", ["0", "-1", "two", "1.5", ""])
def test_r9_rejects_invalid_n_with_usage_error(run_cli, sized_tree, value):
    with pytest.raises(SystemExit) as exc:
        run_cli(sized_tree, "--top", value)
    assert exc.value.code == 2


def test_r9_invalid_n_message_names_the_option(capsys, sized_tree):
    from repolens.cli import main

    with pytest.raises(SystemExit):
        main([str(sized_tree), "--top", "0"])
    out, err = capsys.readouterr()
    assert out == ""
    assert "--top" in err
    assert "usage:" in err


def test_r9_missing_n_is_usage_error(run_cli, sized_tree):
    with pytest.raises(SystemExit) as exc:
        run_cli(sized_tree, "--top")
    assert exc.value.code == 2


def test_r9_without_top_output_is_unchanged(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree)
    assert not out.startswith("Showing")
    assert table_paths(out) == [
        "a_mid.py", "big.py", "pkg/b_mid.py", "small.py", "tiny.py",
    ]


def test_r9_no_python_files_has_no_showing_line(run_cli, fixtures_dir):
    code, out, _ = run_cli(fixtures_dir / "no_python", "--top", "3")
    assert code == 0
    assert out.splitlines()[0] == "No Python files found."
    assert "Showing" not in out
    assert "  Files scanned:  0" in out


def test_r9_parse_error_files_are_ranked_and_keep_marker(run_cli, tmp_path):
    make_file(tmp_path / "ok.py", 2)
    (tmp_path / "bad.py").write_text("def broken(:\n    pass\n    pass\n")
    _, out, _ = run_cli(tmp_path, "--top", "2")
    assert table_paths(out) == ["bad.py", "ok.py"]
    bad_row = next(l for l in out.splitlines() if l.startswith("bad.py"))
    assert bad_row.endswith("(parse error)")


@needs_permissions
def test_r9_unreadable_file_ranks_with_zero_loc(run_cli, tmp_path):
    make_file(tmp_path / "a.py", 2)
    locked = tmp_path / "locked.py"
    make_file(locked, 5)
    locked.chmod(0)
    try:
        _, out, _ = run_cli(tmp_path, "--top", "1")
        assert table_paths(out) == ["a.py"]
        assert "  Files scanned:  2" in out
    finally:
        locked.chmod(0o644)


@needs_permissions
def test_r9_r7_warnings_and_incomplete_line_still_shown(run_cli, tmp_path):
    make_file(tmp_path / "a.py", 2)
    make_file(tmp_path / "b.py", 4)
    locked = tmp_path / "locked"
    make_file(locked / "c.py", 9)
    locked.chmod(0)
    try:
        code, out, err = run_cli(tmp_path, "--top", "1")
        assert code == 0
        assert table_paths(out) == ["b.py"]
        assert "Warning: cannot access folder: locked" in err
        assert out.rstrip("\n").splitlines()[-1].startswith("  Incomplete:")
    finally:
        locked.chmod(0o755)
