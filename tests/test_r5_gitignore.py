"""R5 (changed in Round 4): also leave out paths ignored by .gitignore files.

Trees are built in tmp_path, not tests/fixtures/: a .gitignore committed
under tests/fixtures/ would also make this repository's git ignore the
fixture files it is meant to test."""

import os
import sys

import pytest

from conftest import row_for
from repolens.scanner import find_python_files

needs_permissions = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)
needs_posix_names = pytest.mark.skipif(
    sys.platform == "win32", reason="'*' and trailing spaces are not allowed in Windows names"
)
needs_symlinks = pytest.mark.skipif(
    sys.platform == "win32", reason="creating symlinks needs privileges on Windows"
)


def make_file(path, text="x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def build(root, files, gitignores):
    """Create each .py file and each {folder: text} .gitignore under root."""
    for rel in files:
        make_file(root / rel)
    for folder, text in gitignores.items():
        target = root / folder / ".gitignore" if folder else root / ".gitignore"
        target.parent.mkdir(parents=True, exist_ok=True)
        # newline="" so "\r\n" in a test reaches the file unchanged.
        with open(str(target), "w", newline="") as fh:
            fh.write(text)


def rel_names(root):
    return [p.relative_to(root).as_posix() for p in find_python_files(root)]


def scanned(root, files, gitignore_text):
    """Build files with one root .gitignore and return the scanned paths."""
    build(root, files, {"": gitignore_text})
    return rel_names(root)


@pytest.fixture
def locked_paths():
    """chmod paths to 0 and always restore them afterwards."""
    locked = []

    def _lock(path):
        path.chmod(0)
        locked.append(path)

    yield _lock
    for path in locked:
        path.chmod(0o755 if path.is_dir() or not path.exists() else 0o644)


# --- ignored files and folders ------------------------------------------------


def test_r5_gitignore_ignores_a_named_file(tmp_path):
    names = scanned(tmp_path, ["keep.py", "secret.py"], "secret.py\n")
    assert names == ["keep.py"]


def test_r5_gitignore_name_pattern_matches_at_any_depth(tmp_path):
    names = scanned(tmp_path, ["a/settings.py", "a/b/settings.py", "a/x.py"], "settings.py\n")
    assert names == ["a/x.py"]


def test_r5_gitignore_ignores_a_folder_and_everything_inside(tmp_path):
    names = scanned(tmp_path, ["src/app.py", "build/gen.py", "build/lib/deep.py"], "build/\n")
    assert names == ["src/app.py"]


def test_r5_gitignore_name_without_slash_ignores_folders_too(tmp_path):
    names = scanned(tmp_path, ["src/app.py", "src/dist/out.py"], "dist\n")
    assert names == ["src/app.py"]


def test_r5_gitignore_trailing_slash_matches_folders_only(tmp_path):
    build(tmp_path, ["gen.py", "pkg/x.py"], {"": "gen.py/\npkg/\n"})
    assert rel_names(tmp_path) == ["gen.py"]


def test_r5_gitignore_works_without_a_git_folder(tmp_path):
    assert not (tmp_path / ".git").exists()
    assert scanned(tmp_path, ["a.py", "b.py"], "b.py\n") == ["a.py"]


# --- wildcards ----------------------------------------------------------------


def test_r5_gitignore_star_wildcard(tmp_path):
    names = scanned(tmp_path, ["api.py", "api_pb2.py", "sub/msg_pb2.py"], "*_pb2.py\n")
    assert names == ["api.py"]


def test_r5_gitignore_star_does_not_cross_folders(tmp_path):
    names = scanned(tmp_path, ["src/a.py", "src/sub/b.py"], "src/*.py\n")
    assert names == ["src/sub/b.py"]


def test_r5_gitignore_question_mark_matches_one_character(tmp_path):
    names = scanned(tmp_path, ["t1.py", "t22.py", "t.py"], "t?.py\n")
    assert names == ["t.py", "t22.py"]


def test_r5_gitignore_character_class_and_negated_class(tmp_path):
    files = ["v1.py", "v2.py", "v9.py", "w1.py", "w2.py"]
    names = scanned(tmp_path, files, "v[1-2].py\nw[!1].py\n")
    assert names == ["v9.py", "w1.py"]


def test_r5_gitignore_leading_double_star_matches_any_depth(tmp_path):
    files = ["gen/a.py", "x/gen/b.py", "x/y/gen/c.py", "keep.py"]
    names = scanned(tmp_path, files, "**/gen/\n")
    assert names == ["keep.py"]


def test_r5_gitignore_middle_double_star_matches_zero_or_more_folders(tmp_path):
    files = ["a/b.py", "a/x/b.py", "a/x/y/b.py", "a/c.py", "z/a/b.py"]
    names = scanned(tmp_path, files, "a/**/b.py\n")
    assert names == ["a/c.py", "z/a/b.py"]


def test_r5_gitignore_trailing_double_star_matches_everything_inside(tmp_path):
    names = scanned(tmp_path, ["out/a.py", "out/b/c.py", "outside.py"], "out/**\n")
    assert names == ["outside.py"]


def test_r5_gitignore_matching_is_case_sensitive(tmp_path):
    names = scanned(tmp_path, ["gen.py", "other.py"], "GEN.py\n")
    assert names == ["gen.py", "other.py"]


# --- anchoring ----------------------------------------------------------------


def test_r5_gitignore_leading_slash_anchors_to_gitignore_folder(tmp_path):
    names = scanned(tmp_path, ["conf.py", "pkg/conf.py"], "/conf.py\n")
    assert names == ["pkg/conf.py"]


def test_r5_gitignore_middle_slash_anchors_pattern(tmp_path):
    names = scanned(tmp_path, ["src/gen.py", "lib/src/gen.py"], "src/gen.py\n")
    assert names == ["lib/src/gen.py"]


# --- negation and precedence --------------------------------------------------


def test_r5_gitignore_negation_reincludes_a_file(tmp_path):
    names = scanned(tmp_path, ["a.py", "b.py", "keep.py"], "*.py\n!keep.py\n")
    assert names == ["keep.py"]


def test_r5_gitignore_last_matching_rule_wins(tmp_path):
    names = scanned(tmp_path, ["keep.py", "other.py"], "!keep.py\n*.py\n")
    assert names == []


def test_r5_gitignore_cannot_reinclude_file_inside_ignored_folder(tmp_path):
    names = scanned(tmp_path, ["build/keep.py", "main.py"], "build/\n!build/keep.py\n")
    assert names == ["main.py"]


def test_r5_gitignore_can_reinclude_inside_folder_ignored_with_double_star(tmp_path):
    # "out/**" ignores what is inside out/, not out/ itself, so git (and
    # RepoLens) still enter out/ and the "!" rule can bring a file back.
    names = scanned(tmp_path, ["out/a.py", "out/keep.py"], "out/**\n!out/keep.py\n")
    assert names == ["out/keep.py"]


# --- nested .gitignore files --------------------------------------------------


def test_r5_nested_gitignore_applies_only_below_its_folder(tmp_path):
    build(tmp_path, ["tmp.py", "pkg/tmp.py", "pkg/ok.py"], {"pkg": "tmp.py\n"})
    assert rel_names(tmp_path) == ["pkg/ok.py", "tmp.py"]


def test_r5_nested_gitignore_patterns_are_relative_to_its_folder(tmp_path):
    files = ["conf.py", "pkg/conf.py", "pkg/sub/conf.py", "pkg/gen/x.py", "gen/y.py"]
    build(tmp_path, files, {"pkg": "/conf.py\n/gen/\n"})
    assert rel_names(tmp_path) == ["conf.py", "gen/y.py", "pkg/sub/conf.py"]


def test_r5_nested_gitignore_overrides_parent_rules(tmp_path):
    files = ["gen_a.py", "pkg/gen_a.py", "pkg/gen_keep.py"]
    build(tmp_path, files, {"": "gen_*.py\n", "pkg": "!gen_keep.py\n"})
    assert rel_names(tmp_path) == ["pkg/gen_keep.py"]


def test_r5_parent_rules_still_apply_below_nested_gitignore(tmp_path):
    files = ["pkg/a.py", "pkg/secret.py", "pkg/b.py"]
    build(tmp_path, files, {"": "secret.py\n", "pkg": "b.py\n"})
    assert rel_names(tmp_path) == ["pkg/a.py"]


def test_r5_gitignore_outside_scanned_folder_is_not_read(tmp_path):
    root = tmp_path / "project"
    build(tmp_path, ["project/app.py"], {"": "*.py\n"})
    assert rel_names(root) == ["app.py"]


# --- syntax details -----------------------------------------------------------


def test_r5_gitignore_comments_and_blank_lines_match_nothing(tmp_path):
    text = "# a.py\n\n   \nb.py\n"
    names = scanned(tmp_path, ["a.py", "b.py", "c.py"], text)
    assert names == ["a.py", "c.py"]


def test_r5_gitignore_escaped_hash_and_bang_are_literal(tmp_path):
    names = scanned(tmp_path, ["#x.py", "!y.py", "z.py"], "\\#x.py\n\\!y.py\n")
    assert names == ["z.py"]


def test_r5_gitignore_trailing_spaces_and_crlf_are_removed(tmp_path):
    names = scanned(tmp_path, ["a.py", "b.py", "c.py"], "a.py   \r\nb.py\r\n")
    assert names == ["c.py"]


@needs_posix_names
def test_r5_gitignore_escaped_trailing_space_is_kept(tmp_path):
    # "d\ " means the folder name "d " (with a space), so folder "d" stays.
    names = scanned(tmp_path, ["d/a.py", "d /b.py"], "d\\ \n")
    assert names == ["d/a.py"]


def test_r5_gitignore_unclosed_bracket_pattern_matches_nothing(tmp_path):
    # Same as git: "x[.py" is not a valid class, so the rule never matches.
    names = scanned(tmp_path, ["x[.py", "y.py"], "x[.py\ny.py\n")
    assert names == ["x[.py"]


@needs_posix_names
def test_r5_gitignore_backslash_escapes_wildcards(tmp_path):
    names = scanned(tmp_path, ["a*.py", "ab.py"], "a\\*.py\n")
    assert names == ["ab.py"]


# --- default skip list --------------------------------------------------------


def test_r5_default_dirs_stay_skipped_even_if_gitignore_reincludes_them(tmp_path):
    files = ["keep.py", "venv/a.py", ".venv/b.py", "__pycache__/c.py"]
    text = "!venv/\n!.venv/\n!__pycache__/\n!venv\n"
    assert scanned(tmp_path, files, text) == ["keep.py"]


def test_r5_default_dirs_and_gitignore_rules_both_apply(tmp_path):
    files = ["keep.py", "venv/a.py", "build/b.py"]
    assert scanned(tmp_path, files, "build/\n") == ["keep.py"]


# --- interaction with R7 and R8 ----------------------------------------------


@needs_permissions
def test_r5_ignored_unreadable_folder_gives_no_r7_warning(run_cli, tmp_path, locked_paths):
    build(tmp_path, ["keep.py", "cache/x.py"], {"": "cache/\n"})
    locked_paths(tmp_path / "cache")
    code, out, err = run_cli(tmp_path)
    assert code == 0
    assert err == ""
    assert "Incomplete:" not in out


@needs_permissions
def test_r5_unreadable_gitignore_warns_and_scan_continues(run_cli, tmp_path, locked_paths):
    build(tmp_path, ["keep.py", "pkg/gen.py"], {"pkg": "gen.py\n"})
    locked_paths(tmp_path / "pkg" / ".gitignore")
    code, out, err = run_cli(tmp_path)
    assert code == 0
    assert err.splitlines() == ["Warning: cannot read .gitignore: pkg/.gitignore"]
    # Treated as empty, so its rule does not apply.
    assert row_for(out, "pkg/gen.py") == (1, 0, 0)
    assert "Files scanned:  2" in out
    assert "Incomplete:" not in out


@needs_permissions
def test_r5_gitignore_warning_comes_after_folder_warnings(run_cli, tmp_path, locked_paths):
    build(tmp_path, ["keep.py", "a/x.py"], {"": "x.py\n"})
    locked_paths(tmp_path / ".gitignore")
    locked_paths(tmp_path / "a")
    _, _, err = run_cli(tmp_path)
    assert err.splitlines() == [
        "Warning: cannot access folder: a",
        "Warning: cannot read .gitignore: .gitignore",
    ]


@needs_symlinks
def test_r5_symlink_is_matched_by_its_own_path(tmp_path):
    make_file(tmp_path / "gen" / "real.py")
    (tmp_path / "link.py").symlink_to(tmp_path / "gen" / "real.py")
    build(tmp_path, [], {"": "gen/\n"})
    assert rel_names(tmp_path) == ["link.py"]


def test_r5_ignored_hard_link_does_not_hide_the_kept_path(tmp_path):
    make_file(tmp_path / "src" / "real.py")
    try:
        os.link(str(tmp_path / "src" / "real.py"), str(tmp_path / "copy.py"))
    except (OSError, AttributeError):
        pytest.skip("hard links not supported here")
    build(tmp_path, [], {"": "src/\n"})
    assert rel_names(tmp_path) == ["copy.py"]


# --- CLI output ---------------------------------------------------------------


def test_r5_cli_leaves_ignored_files_out_of_rows_and_summary(run_cli, tmp_path):
    make_file(tmp_path / "main.py", "def f():\n    pass\n")
    make_file(tmp_path / "gen" / "big.py", "class A:\n    pass\n" * 10)
    build(tmp_path, [], {"": "gen/\n"})
    code, out, err = run_cli(tmp_path)
    assert code == 0
    assert err == ""
    assert "big.py" not in out
    assert row_for(out, "main.py") == (2, 1, 0)
    assert "Files scanned:  1" in out
    assert "Lines of code:  2" in out
    assert "Classes:        0" in out


def test_r5_cli_with_everything_ignored_prints_no_files_found(run_cli, tmp_path):
    build(tmp_path, ["a.py", "b/c.py"], {"": "*.py\n"})
    code, out, _ = run_cli(tmp_path)
    assert code == 0
    assert "No Python files found." in out
    assert "Files scanned:  0" in out


def test_r5_cli_top_ranks_only_files_that_are_not_ignored(run_cli, tmp_path):
    make_file(tmp_path / "small.py", "x = 1\n")
    make_file(tmp_path / "vendor" / "huge.py", "x = 1\n" * 50)
    build(tmp_path, [], {"": "vendor/\n"})
    _, out, _ = run_cli(tmp_path, "--top", "1")
    assert out.splitlines()[0] == "Showing the 1 largest of 1 files (ranked by lines of code)."
    assert "huge.py" not in out
