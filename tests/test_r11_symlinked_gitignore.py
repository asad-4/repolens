"""R11 (Round 6): a .gitignore that is a symbolic link is skipped, not followed.

Trees are built in tmp_path, never in tests/fixtures/ (see CLAUDE.md).
"""

import json
import os
import sys

import pytest

from repolens.report import format_json
from repolens.scanner import FileStats, discover, scan

needs_symlinks = pytest.mark.skipif(
    sys.platform == "win32", reason="creating symlinks needs privileges on Windows"
)
needs_permissions = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)

pytestmark = needs_symlinks


def make_file(path, text="x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def warning(rel):
    return "Warning: skipped .gitignore that is a symlink: {}".format(rel)


def listed(stdout):
    """Paths in the table rows (first column after the header and dashes)."""
    rows = stdout.split("\n\nSummary")[0].splitlines()[2:]
    return [r.split()[0] for r in rows]


@pytest.fixture
def project(tmp_path):
    """tmp_path/proj with a.py, b.py; tmp_path/outside holds rules 'a.py'."""
    root = tmp_path / "proj"
    make_file(root / "a.py")
    make_file(root / "b.py")
    make_file(tmp_path / "outside" / "rules", "a.py\n")
    return root


# --- the link is not followed and its rules are not applied ----------------------


def test_r11_link_to_file_outside_folder_is_not_applied(run_cli, project):
    (project / ".gitignore").symlink_to(project.parent / "outside" / "rules")
    code, out, err = run_cli(project)
    assert code == 0
    assert listed(out) == ["a.py", "b.py"]
    assert err.splitlines() == [warning(".gitignore")]


def test_r11_link_to_file_inside_folder_is_not_applied(run_cli, project):
    make_file(project / "rules.txt", "a.py\n")
    (project / ".gitignore").symlink_to(project / "rules.txt")
    _, out, err = run_cli(project)
    assert listed(out) == ["a.py", "b.py"]
    assert err.splitlines() == [warning(".gitignore")]


def test_r11_link_to_another_gitignore_applies_only_where_the_real_file_is(
    run_cli, tmp_path
):
    make_file(tmp_path / "x" / "a.py")
    make_file(tmp_path / "x" / ".gitignore", "a.py\n")
    make_file(tmp_path / "y" / "a.py")
    (tmp_path / "y" / ".gitignore").symlink_to(tmp_path / "x" / ".gitignore")
    _, out, err = run_cli(tmp_path)
    assert listed(out) == ["y/a.py"]
    assert err.splitlines() == [warning("y/.gitignore")]


@needs_permissions
def test_r11_link_target_is_never_opened(run_cli, project):
    target = project.parent / "outside" / "rules"
    (project / ".gitignore").symlink_to(target)
    target.chmod(0o000)
    try:
        _, out, err = run_cli(project)
    finally:
        target.chmod(0o644)
    # Opening the target would have failed with "cannot read .gitignore".
    assert err.splitlines() == [warning(".gitignore")]
    assert listed(out) == ["a.py", "b.py"]


def test_r11_relative_link_is_skipped(run_cli, project):
    (project / ".gitignore").symlink_to(os.path.join("..", "outside", "rules"))
    _, out, err = run_cli(project)
    assert listed(out) == ["a.py", "b.py"]
    assert err.splitlines() == [warning(".gitignore")]


# --- broken links, loops, links to folders ----------------------------------------


def test_r11_broken_link_is_reported_as_symlink_not_unreadable(run_cli, project):
    (project / ".gitignore").symlink_to(project / "missing")
    code, out, err = run_cli(project)
    assert code == 0
    assert err.splitlines() == [warning(".gitignore")]
    assert listed(out) == ["a.py", "b.py"]


def test_r11_link_loop_is_skipped(run_cli, project):
    (project / ".gitignore").symlink_to(project / ".gitignore")
    _, out, err = run_cli(project)
    assert err.splitlines() == [warning(".gitignore")]
    assert listed(out) == ["a.py", "b.py"]


def test_r11_link_to_folder_named_gitignore_is_skipped(run_cli, project):
    make_file(project.parent / "somedir" / "inner.py")
    (project / ".gitignore").symlink_to(project.parent / "somedir")
    _, out, err = run_cli(project)
    assert err.splitlines() == [warning(".gitignore")]
    # Folder links are still not followed (R1).
    assert listed(out) == ["a.py", "b.py"]


# --- other .gitignore files keep working --------------------------------------------


def test_r11_parent_rules_still_apply_below_a_symlinked_gitignore(run_cli, tmp_path):
    make_file(tmp_path / ".gitignore", "gen_*.py\n")
    make_file(tmp_path / "pkg" / "gen_x.py")
    make_file(tmp_path / "pkg" / "keep.py")
    make_file(tmp_path / "pkg" / "rules", "keep.py\n")
    (tmp_path / "pkg" / ".gitignore").symlink_to(tmp_path / "pkg" / "rules")
    _, out, err = run_cli(tmp_path)
    assert listed(out) == ["pkg/keep.py"]
    assert err.splitlines() == [warning("pkg/.gitignore")]


def test_r11_regular_gitignore_beside_symlinked_one_still_applies(run_cli, tmp_path):
    make_file(tmp_path / "real" / ".gitignore", "a.py\n")
    make_file(tmp_path / "real" / "a.py")
    make_file(tmp_path / "linked" / "a.py")
    (tmp_path / "linked" / ".gitignore").symlink_to(tmp_path / "real" / ".gitignore")
    _, out, _ = run_cli(tmp_path)
    assert listed(out) == ["linked/a.py"]


def test_r11_hard_linked_gitignore_is_read(run_cli, project):
    target = project.parent / "outside" / "rules"
    os.link(str(target), str(project / ".gitignore"))
    _, out, err = run_cli(project)
    assert err == ""
    assert listed(out) == ["b.py"]


def test_r11_no_warning_without_symlinks(run_cli, project):
    make_file(project / ".gitignore", "a.py\n")
    _, out, err = run_cli(project)
    assert err == ""
    assert listed(out) == ["b.py"]


# --- links that are never seen ------------------------------------------------------


def test_r11_link_inside_ignored_folder_gives_no_warning(run_cli, project):
    make_file(project / ".gitignore", "build/\n")
    make_file(project / "build" / "x.py")
    (project / "build" / ".gitignore").symlink_to(project / "missing")
    _, out, err = run_cli(project)
    assert err == ""
    assert listed(out) == ["a.py", "b.py"]


def test_r11_link_inside_default_skipped_folder_gives_no_warning(run_cli, project):
    (project / "venv").mkdir()
    (project / "venv" / ".gitignore").symlink_to(project / "missing")
    _, _, err = run_cli(project)
    assert err == ""


# --- warnings: wording, order, exit status, summary ---------------------------------


def test_r11_warnings_sorted_by_path(run_cli, tmp_path):
    for folder in ["b", "a/z", ""]:
        d = tmp_path / folder if folder else tmp_path
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitignore").symlink_to(tmp_path / "missing")
    make_file(tmp_path / "m.py")
    _, _, err = run_cli(tmp_path)
    assert err.splitlines() == [
        warning(".gitignore"),
        warning("a/z/.gitignore"),
        warning("b/.gitignore"),
    ]


@needs_permissions
def test_r11_warnings_come_after_folder_and_unreadable_warnings(run_cli, tmp_path):
    make_file(tmp_path / "m.py")
    locked = tmp_path / "locked"
    locked.mkdir()
    unreadable = tmp_path / "u" / ".gitignore"
    make_file(unreadable, "*.py\n")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / ".gitignore").symlink_to(tmp_path / "missing")
    locked.chmod(0o000)
    unreadable.chmod(0o000)
    try:
        code, out, err = run_cli(tmp_path)
    finally:
        locked.chmod(0o755)
        unreadable.chmod(0o644)
    assert code == 0
    assert err.splitlines() == [
        "Warning: cannot access folder: locked",
        "Warning: cannot read .gitignore: u/.gitignore",
        warning("a/.gitignore"),
    ]
    # Only the inaccessible folder makes the scan incomplete.
    assert "  Incomplete:     1 folder(s) could not be accessed (see warnings)" in out


def test_r11_summary_has_no_incomplete_line(run_cli, project):
    (project / ".gitignore").symlink_to(project / "missing")
    code, out, _ = run_cli(project)
    assert code == 0
    assert "Incomplete" not in out
    assert out.endswith("  Classes:        0\n")


def test_r11_table_matches_scan_without_any_gitignore(run_cli, project):
    _, before, _ = run_cli(project)
    (project / ".gitignore").symlink_to(project.parent / "outside" / "rules")
    _, after, _ = run_cli(project)
    assert after == before


def test_r11_works_with_top(run_cli, project):
    (project / ".gitignore").symlink_to(project.parent / "outside" / "rules")
    _, out, err = run_cli(project, "--top", "1")
    assert out.startswith("Showing the 1 largest of 2 files")
    assert err.splitlines() == [warning(".gitignore")]


# --- JSON (R10) ----------------------------------------------------------------------


def test_r11_json_lists_symlinked_gitignores_last(run_cli, tmp_path):
    make_file(tmp_path / "a.py")
    for folder in ["q", "p"]:
        (tmp_path / folder).mkdir()
        (tmp_path / folder / ".gitignore").symlink_to(tmp_path / "missing")
    code, out, err = run_cli(tmp_path, "--format", "json")
    assert code == 0
    data = json.loads(out)
    assert list(data)[-1] == "symlinked_gitignores"
    assert data["symlinked_gitignores"] == ["p/.gitignore", "q/.gitignore"]
    assert data["unreadable_gitignores"] == []
    assert data["inaccessible_folders"] == []
    assert err.splitlines() == [warning("p/.gitignore"), warning("q/.gitignore")]


def test_r11_json_empty_list_when_no_symlinks(run_cli, project):
    _, out, _ = run_cli(project, "--format", "json")
    assert json.loads(out)["symlinked_gitignores"] == []


def test_r11_json_files_ignore_link_rules(run_cli, project):
    (project / ".gitignore").symlink_to(project.parent / "outside" / "rules")
    _, out, _ = run_cli(project, "--format", "json")
    data = json.loads(out)
    assert [f["path"] for f in data["files"]] == ["a.py", "b.py"]
    assert data["summary"]["files_scanned"] == 2


def test_r11_format_json_takes_symlinked_gitignores():
    stats = [FileStats("a.py", 1, 0, 0)]
    data = json.loads(format_json(stats, [], [], None, ["x/.gitignore"]))
    assert data["symlinked_gitignores"] == ["x/.gitignore"]
    # Older callers that pass four arguments get an empty list.
    assert json.loads(format_json(stats, [], [], None))["symlinked_gitignores"] == []


# --- scanner API ---------------------------------------------------------------------


def test_r11_discover_and_scan_record_symlinked_gitignores(project):
    (project / ".gitignore").symlink_to(project.parent / "outside" / "rules")
    found = discover(project)
    assert found.symlinked_gitignores == [".gitignore"]
    assert found.unreadable_gitignores == []
    assert [p.name for p in found.files] == ["a.py", "b.py"]
    assert scan(project).symlinked_gitignores == [".gitignore"]
