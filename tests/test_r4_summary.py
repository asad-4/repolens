def summary_values(stdout):
    """Parse the Summary block into a dict of label -> int."""
    lines = stdout.splitlines()
    start = lines.index("Summary")
    values = {}
    for line in lines[start + 1:]:
        label, _, number = line.strip().rpartition(":")
        values[label.strip()] = int(number)
    return values


def test_r4_summary_appears_after_file_list(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic")
    lines = out.splitlines()
    assert lines.index("Summary") > max(
        i for i, l in enumerate(lines) if ".py" in l
    )


def test_r4_summary_totals(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic")
    assert summary_values(out) == {
        "Files scanned": 4,
        "Lines of code": 14,
        "Functions": 4,
        "Classes": 2,
    }


def test_r4_summary_includes_files_with_parse_errors(run_cli, fixtures_dir):
    # broken/: bad_syntax(2 loc) + good(2 loc, 1 func) + unterminated(2 loc)
    _, out, _ = run_cli(fixtures_dir / "broken")
    assert summary_values(out) == {
        "Files scanned": 3,
        "Lines of code": 6,
        "Functions": 1,
        "Classes": 0,
    }


def test_r4_no_python_files_shows_message_and_zero_summary(run_cli, fixtures_dir):
    code, out, _ = run_cli(fixtures_dir / "no_python")
    assert code == 0
    assert "No Python files found." in out
    assert summary_values(out) == {
        "Files scanned": 0,
        "Lines of code": 0,
        "Functions": 0,
        "Classes": 0,
    }
