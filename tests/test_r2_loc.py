from conftest import row_for
from repolens.scanner import count_loc


def test_r2_shows_relative_paths_with_forward_slashes(run_cli, fixtures_dir):
    code, out, _ = run_cli(fixtures_dir / "basic")
    assert code == 0
    assert "pkg/sub/deep.py" in out
    # Absolute fixture path must not leak into per-file rows.
    assert str(fixtures_dir) not in out


def test_r2_lists_files_in_sorted_order(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic")
    order = [
        line.split()[0]
        for line in out.splitlines()
        if line.split() and line.split()[0].endswith(".py")
    ]
    assert order == sorted(order)


def test_r2_counts_loc_per_file(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic")
    assert row_for(out, "main.py")[0] == 5
    assert row_for(out, "pkg/__init__.py")[0] == 0
    assert row_for(out, "pkg/models.py")[0] == 7
    assert row_for(out, "pkg/sub/deep.py")[0] == 2


def test_r2_excludes_blank_and_comment_lines(fixtures_dir):
    # sample.py: docstring(1) + import(1) + x, y(2) + def(1)
    #            + 3-line docstring(3) + return(1) = 9
    source = (fixtures_dir / "loc" / "sample.py").read_bytes()
    assert count_loc(source) == 9


def test_r2_line_with_trailing_comment_counts():
    assert count_loc(b"x = 1  # set x\n") == 1


def test_r2_hash_inside_string_is_not_a_comment():
    assert count_loc(b's = "# hi"\n') == 1


def test_r2_comment_only_and_blank_lines_count_zero():
    assert count_loc(b"# one\n\n   \n    # two\n") == 0


def test_r2_falls_back_when_file_cannot_be_tokenized(fixtures_dir):
    # Unterminated triple-quoted string; fallback counts non-blank, non-# lines.
    source = (fixtures_dir / "broken" / "unterminated.py").read_bytes()
    assert count_loc(source) == 2
