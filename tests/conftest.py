from pathlib import Path

import pytest

from repolens.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES


@pytest.fixture
def run_cli(capsys):
    """Run the CLI in-process; return (exit_code, stdout, stderr)."""

    def _run(*args):
        code = main([str(a) for a in args])
        out, err = capsys.readouterr()
        return code, out, err

    return _run


def row_for(stdout, rel_path):
    """Return the numbers (loc, functions, classes) on the row for rel_path."""
    for line in stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == rel_path:
            return int(parts[1]), int(parts[2]), int(parts[3])
    raise AssertionError("no row for {!r} in output:\n{}".format(rel_path, stdout))
