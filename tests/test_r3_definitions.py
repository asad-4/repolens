import os
import sys

import pytest

from conftest import row_for
from repolens.scanner import count_definitions


def test_r3_counts_async_functions(fixtures_dir):
    source = (fixtures_dir / "counts" / "only_async.py").read_bytes()
    assert count_definitions(source) == (2, 0)


def test_r3_counts_methods_nested_functions_and_nested_classes(fixtures_dir):
    # shapes.py: sync_func, async_func, method, inner, async_method = 5 functions
    #            Outer, Inner = 2 classes; the lambda is not counted.
    source = (fixtures_dir / "counts" / "shapes.py").read_bytes()
    assert count_definitions(source) == (5, 2)


def test_r3_does_not_count_lambdas():
    assert count_definitions(b"f = lambda x: x\n") == (0, 0)


def test_r3_shows_counts_per_file(run_cli, fixtures_dir):
    _, out, _ = run_cli(fixtures_dir / "basic")
    assert row_for(out, "main.py")[1:] == (1, 0)
    assert row_for(out, "pkg/models.py")[1:] == (2, 2)
    assert row_for(out, "pkg/sub/deep.py")[1:] == (1, 0)


def test_r3_syntax_error_file_is_marked_and_scan_continues(run_cli, fixtures_dir):
    code, out, _ = run_cli(fixtures_dir / "broken")
    assert code == 0
    bad_row = next(l for l in out.splitlines() if l.startswith("bad_syntax.py"))
    assert "(parse error)" in bad_row
    assert row_for(out, "bad_syntax.py")[1:] == (0, 0)
    assert row_for(out, "good.py") == (2, 1, 0)


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced on Windows or for root",
)
def test_r3_unreadable_file_is_marked_and_scan_continues(run_cli, tmp_path):
    locked = tmp_path / "locked.py"
    locked.write_text("def f():\n    pass\n")
    locked.chmod(0)
    (tmp_path / "open.py").write_text("class A:\n    pass\n")
    try:
        code, out, _ = run_cli(tmp_path)
    finally:
        locked.chmod(0o644)
    assert code == 0
    assert "(unreadable)" in out
    assert row_for(out, "locked.py") == (0, 0, 0)
    assert row_for(out, "open.py") == (2, 0, 1)


def test_r3_undecodable_file_does_not_crash(run_cli, tmp_path):
    (tmp_path / "binary.py").write_bytes(b"\xff\xfe\x00\x01garbage\n")
    code, out, _ = run_cli(tmp_path)
    assert code == 0
    assert "(parse error)" in out
