"""``sigil_core.PARSER_TESTS`` is the parser suite's real size (bojio clean
break P-SI-3 S1). Aetheria quotes it; once Sigil lives in its own repo this is
the only place the count can be checked against the suite, so it lives here,
outside ``tests/`` so it does not count itself.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def _collected(path: Path) -> int:
    proc = subprocess.run([sys.executable, "-m", "pytest", str(path), "--collect-only", "-q",
                           "--no-header", "-p", "no:cacheprovider"],
                          cwd=PKG, capture_output=True, text=True, timeout=120)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m, proc.stdout[-500:] + proc.stderr[-500:]
    return int(m.group(1))


def test_parser_tests_is_the_suites_real_size():
    sys.path.insert(0, str(PKG))
    import sigil_core
    assert _collected(PKG / "tests") == sigil_core.PARSER_TESTS


def test_the_count_moves_with_the_suite(tmp_path):
    """The probe can see a change: one planted test is one more collected."""
    (tmp_path / "test_x.py").write_text("def test_a():\n    pass\n\ndef test_b():\n    pass\n")
    assert _collected(tmp_path) == 2
