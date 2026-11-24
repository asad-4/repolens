"""R10: --format json prints the report as one JSON object with the same
files and summary totals as the table."""

import json
import os
import sys

import pytest

from conftest import row_for
from repolens.report import format_json, format_report
from repolens.scanner import FileStats

needs_permissions = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)


def make_file(path, loc):
    """Write a .py file with exactly `loc` lines of code."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join("x{} = {}\n".format(i, i) for i in range(loc)))


def table_paths(stdout):
    lines = stdout.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("---")) + 1
    paths = []
    for line in lines[start:]:
        if not line.strip():
            break
        paths.append(line.split()[0])
    return paths


def summary_value(stdout, label):
    for line in stdout.splitlines():
        if line.strip().startswith(label):
            return int(line.split(":")[1])
    raise AssertionError("no {!r} in output".format(label))


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


@pytest.fixture
def sized_tree(tmp_path):
    """Five files: 10, 3, 7, 7 and 1 lines of code (two tie at 7)."""
    make_file(tmp_path / "big.py", 10)
    make_file(tmp_path / "small.py", 3)
    make_file(tmp_path / "pkg/b_mid.py", 7)
    make_file(tmp_path / "a_mid.py", 7)
    make_file(tmp_path / "tiny.py", 1)
    return tmp_path


# --- shape -------------------------------------------------------------------


def test_r10_stdout_is_one_json_object(run_cli, fixtures_dir):
    code, out, err = run_cli(fixtures_dir / "basic", "--format", "json")
    assert code == 0
    assert err == ""
    assert out.endswith("}\n")
    data = json.loads(out)  # raises if anything but JSON is on stdout
    assert isinstance(data, dict)


def test_r10_top_level_keys_in_order(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic", "--format", "json")
    assert list(json.loads(out)) == [
        "files",
        "summary",
        "inaccessible_folders",
        "unreadable_gitignores",
        "top",
    ]


def test_r10_exact_output_for_basic_fixture(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic", "--format", "json")
    assert json.loads(out) == {
        "files": [
            {"path": "main.py", "lines": 5, "functions": 1, "classes": 0, "note": None},
            {"path": "pkg/__init__.py", "lines": 0, "functions": 0, "classes": 0, "note": None},
            {"path": "pkg/models.py", "lines": 7, "functions": 2, "classes": 2, "note": None},
            {"path": "pkg/sub/deep.py", "lines": 2, "functions": 1, "classes": 0, "note": None},
        ],
        "summary": {"files_scanned": 4, "lines_of_code": 14, "functions": 4, "classes": 2},
        "inaccessible_folders": [],
        "unreadable_gitignores": [],
        "top": None,
    }


def test_r10_file_and_summary_keys_in_order(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic", "--format", "json")
    data = json.loads(out)
    assert list(data["files"][0]) == ["path", "lines", "functions", "classes", "note"]
    assert list(data["summary"]) == ["files_scanned", "lines_of_code", "functions", "classes"]


def test_r10_indented_with_two_spaces(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic", "--format", "json")
    lines = out.splitlines()
    assert lines[0] == "{"
    assert lines[1] == '  "files": ['
    assert lines[-1] == "}"


def test_r10_numbers_are_integers(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic", "--format", "json")
    data = json.loads(out)
    for f in data["files"]:
        for key in ("lines", "functions", "classes"):
            assert type(f[key]) is int
    for value in data["summary"].values():
        assert type(value) is int


# --- same files and totals as the table --------------------------------------


@pytest.mark.parametrize("name", ["basic", "broken", "counts", "loc", "no_python"])
def test_r10_same_files_and_totals_as_table(run_cli, fixtures_dir, name):
    _, table, _ = run_cli(fixtures_dir / name)
    _, out, _ = run_cli(fixtures_dir / name, "--format", "json")
    data = json.loads(out)
    paths = [f["path"] for f in data["files"]]
    if paths:
        assert paths == table_paths(table)
    for f in data["files"]:
        assert (f["lines"], f["functions"], f["classes"]) == row_for(table, f["path"])
    s = data["summary"]
    assert s["files_scanned"] == summary_value(table, "Files scanned")
    assert s["lines_of_code"] == summary_value(table, "Lines of code")
    assert s["functions"] == summary_value(table, "Functions")
    assert s["classes"] == summary_value(table, "Classes")


def test_r10_parse_error_note(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "broken", "--format", "json")
    notes = {f["path"]: f["note"] for f in json.loads(out)["files"]}
    assert notes["bad_syntax.py"] == "parse error"
    assert notes["good.py"] is None


@needs_permissions
def test_r10_unreadable_note(run_cli, tmp_path):
    make_file(tmp_path / "ok.py", 2)
    locked = tmp_path / "locked.py"
    make_file(locked, 3)
    locked.chmod(0)
    try:
        _, out, _ = run_cli(tmp_path, "--format", "json")
    finally:
        locked.chmod(0o644)
    files = json.loads(out)["files"]
    assert files[0] == {
        "path": "locked.py", "lines": 0, "functions": 0, "classes": 0, "note": "unreadable"
    }


def test_r10_no_python_files_gives_empty_list_and_zeros(run_cli, fixtures_dir):
    code, out, err = run_cli(fixtures_dir / "no_python", "--format", "json")
    assert code == 0
    assert err == ""
    assert "No Python files found." not in out
    data = json.loads(out)
    assert data["files"] == []
    assert data["summary"] == {
        "files_scanned": 0, "lines_of_code": 0, "functions": 0, "classes": 0
    }


def test_r10_gitignored_files_are_left_out(run_cli, tmp_path):
    make_file(tmp_path / "keep.py", 1)
    make_file(tmp_path / "build/gen.py", 5)
    (tmp_path / ".gitignore").write_text("build/\n")
    _, out, _ = run_cli(tmp_path, "--format", "json")
    data = json.loads(out)
    assert [f["path"] for f in data["files"]] == ["keep.py"]
    assert data["summary"]["files_scanned"] == 1


# --- --top (R9) ----------------------------------------------------------------


def test_r10_top_limits_and_ranks_files(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--format", "json", "--top", "3")
    data = json.loads(out)
    assert [f["path"] for f in data["files"]] == ["big.py", "a_mid.py", "pkg/b_mid.py"]
    assert data["top"] == 3


def test_r10_top_rows_match_table_rows(run_cli, sized_tree):
    _, table, _ = run_cli(sized_tree, "--top", "2")
    _, out, _ = run_cli(sized_tree, "--top", "2", "--format", "json")
    assert [f["path"] for f in json.loads(out)["files"]] == table_paths(table)


def test_r10_top_summary_counts_every_file(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "1", "--format", "json")
    data = json.loads(out)
    assert len(data["files"]) == 1
    assert data["summary"] == {
        "files_scanned": 5, "lines_of_code": 28, "functions": 0, "classes": 0
    }


def test_r10_top_larger_than_file_count(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "99", "--format", "json")
    data = json.loads(out)
    assert len(data["files"]) == 5
    assert data["top"] == 99


def test_r10_top_has_no_showing_line(run_cli, sized_tree):
    _, out, _ = run_cli(sized_tree, "--top", "2", "--format", "json")
    assert "Showing" not in out
    assert out.startswith("{")


# --- warnings (R7, R5 .gitignore) ---------------------------------------------


@needs_permissions
def test_r10_inaccessible_folders_on_stderr_and_in_json(run_cli, tmp_path, locked_dirs):
    make_file(tmp_path / "keep.py", 2)
    make_file(tmp_path / "b/x.py", 1)
    make_file(tmp_path / "a/y.py", 1)
    locked_dirs(tmp_path / "b")
    locked_dirs(tmp_path / "a")
    code, out, err = run_cli(tmp_path, "--format", "json")
    assert code == 0
    assert err.splitlines() == [
        "Warning: cannot access folder: a",
        "Warning: cannot access folder: b",
    ]
    data = json.loads(out)
    assert data["inaccessible_folders"] == ["a", "b"]
    assert [f["path"] for f in data["files"]] == ["keep.py"]
    assert "Incomplete" not in out


@needs_permissions
def test_r10_unreadable_gitignore_on_stderr_and_in_json(run_cli, tmp_path):
    make_file(tmp_path / "pkg/x.py", 1)
    gi = tmp_path / "pkg/.gitignore"
    gi.write_text("x.py\n")
    gi.chmod(0)
    try:
        code, out, err = run_cli(tmp_path, "--format", "json")
    finally:
        gi.chmod(0o644)
    assert code == 0
    assert err.splitlines() == ["Warning: cannot read .gitignore: pkg/.gitignore"]
    data = json.loads(out)
    assert data["unreadable_gitignores"] == ["pkg/.gitignore"]
    assert data["inaccessible_folders"] == []
    assert [f["path"] for f in data["files"]] == ["pkg/x.py"]


# --- option values and errors ---------------------------------------------------


def test_r10_format_table_is_the_default(run_cli, fixtures_dir):
    _, default, _ = run_cli(fixtures_dir / "basic")
    _, table, _ = run_cli(fixtures_dir / "basic", "--format", "table")
    assert table == default
    assert table.startswith("File ")


def test_r10_format_equals_syntax_and_any_position(run_cli, fixtures_dir):
    _, before, _ = run_cli("--format=json", fixtures_dir / "basic")
    _, after, _ = run_cli(fixtures_dir / "basic", "--format", "json")
    assert before == after
    json.loads(before)


@pytest.mark.parametrize("value", ["JSON", "csv", "", "text"])
def test_r10_invalid_format_is_a_usage_error(run_cli, fixtures_dir, value):
    with pytest.raises(SystemExit) as exc:
        run_cli(fixtures_dir / "basic", "--format", value)
    assert exc.value.code == 2


def test_r10_invalid_format_prints_nothing_on_stdout(capsys, fixtures_dir):
    from repolens.cli import main

    with pytest.raises(SystemExit):
        main([str(fixtures_dir / "basic"), "--format", "xml"])
    out, err = capsys.readouterr()
    assert out == ""
    assert "invalid choice" in err


def test_r10_missing_folder_error_stays_text(run_cli, tmp_path):
    missing = tmp_path / "nope"
    code, out, err = run_cli(missing, "--format", "json")
    assert code == 1
    assert out == ""
    assert err == "Error: folder not found: {}\n".format(missing)


def test_r10_not_a_folder_error_stays_text(run_cli, fixtures_dir):
    target = fixtures_dir / "basic" / "main.py"
    code, out, err = run_cli(target, "--format", "json")
    assert code == 1
    assert out == ""
    assert err.startswith("Error: not a folder:")


# --- encoding ------------------------------------------------------------------


def test_r10_non_ascii_paths_are_escaped(run_cli, tmp_path):
    make_file(tmp_path / "café.py", 2)
    _, out, _ = run_cli(tmp_path, "--format", "json")
    assert out.isascii()
    assert "caf\\u00e9.py" in out
    assert json.loads(out)["files"][0]["path"] == "café.py"


def test_r10_special_characters_in_paths_are_valid_json(run_cli, tmp_path):
    if sys.platform == "win32":
        pytest.skip("names with backslash or quotes are not allowed on Windows")
    make_file(tmp_path / 'we"ird\\name.py', 1)
    _, out, _ = run_cli(tmp_path, "--format", "json")
    assert json.loads(out)["files"][0]["path"] == 'we"ird\\name.py'


# --- report function --------------------------------------------------------------


def test_r10_format_json_matches_format_report_totals():
    stats = [
        FileStats("b.py", 4, 1, 0),
        FileStats("a.py", 9, 2, 1, "parse error"),
    ]
    data = json.loads(format_json(stats, ["x"], ["y/.gitignore"], top=1))
    assert data["files"] == [
        {"path": "a.py", "lines": 9, "functions": 2, "classes": 1, "note": "parse error"}
    ]
    assert data["summary"] == {
        "files_scanned": 2, "lines_of_code": 13, "functions": 3, "classes": 1
    }
    assert data["inaccessible_folders"] == ["x"]
    assert data["unreadable_gitignores"] == ["y/.gitignore"]
    assert data["top"] == 1
    # The table built from the same input shows the same totals.
    assert "  Lines of code:  13" in format_report(stats, 1, 1)


def test_r10_table_output_unchanged_without_format(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic")
    assert out.splitlines()[:2] == [
        "File             Lines  Functions  Classes",
        "---------------  -----  ---------  -------",
    ]
    assert "{" not in out
