"""Validate every Sigil code block in the whitepaper parses correctly.

This is the acid test: if a whitepaper example doesn't parse with the
shipped v0.5.0 parser, the whitepaper is wrong, not the parser.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sigil_core import parse

# Path to whitepaper relative to this test file
WHITEPAPER = Path(__file__).resolve().parents[3] / "docs" / "aetheria-whitepaper.md"


def _extract_sigil_blocks(md_path: Path) -> list[tuple[int, str]]:
    """Extract all ```sigil code blocks from a markdown file.

    Returns list of (line_number, code_block_content) tuples.
    """
    text = md_path.read_text(encoding="utf-8")
    blocks: list[tuple[int, str]] = []

    # Find all ```sigil ... ``` blocks
    pattern = re.compile(
        r"^```sigil\s*\n(.*?)^```",
        re.MULTILINE | re.DOTALL,
    )

    for match in pattern.finditer(text):
        # Calculate line number of the opening fence
        line_num = text[: match.start()].count("\n") + 1
        code = match.group(1).strip()
        if code:
            blocks.append((line_num, code))

    return blocks


# Extract blocks once at module level
_BLOCKS = _extract_sigil_blocks(WHITEPAPER) if WHITEPAPER.exists() else []


def _block_id(item: tuple[int, str]) -> str:
    """Generate a short test ID from line number and first tokens."""
    line, code = item
    # Take first meaningful line (skip comments)
    for raw_line in code.splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith(";;"):
            # Truncate for readability
            label = stripped[:60].replace(" ", "_")
            return f"L{line}_{label}"
    return f"L{line}_comment_only"


@pytest.mark.parametrize("block", _BLOCKS, ids=[_block_id(b) for b in _BLOCKS])
def test_whitepaper_block_parses(block: tuple[int, str]) -> None:
    """Each Sigil block in the whitepaper must parse without error."""
    line_num, code = block

    # Strip comment-only lines for parse (comments are lexer-level, should work)
    # But we still parse the full block including comments
    try:
        nodes = parse(code)
    except Exception as exc:
        pytest.fail(
            f"Whitepaper line {line_num}: parse error\n"
            f"Code:\n{code}\n"
            f"Error: {exc}"
        )

    # Every block should produce at least one AST node
    assert len(nodes) > 0, (
        f"Whitepaper line {line_num}: parsed but produced no AST nodes\n"
        f"Code:\n{code}"
    )


def test_whitepaper_exists() -> None:
    """The whitepaper file must exist."""
    assert WHITEPAPER.exists(), f"Whitepaper not found at {WHITEPAPER}"


def test_whitepaper_has_sigil_blocks() -> None:
    """The whitepaper must contain Sigil code blocks."""
    assert len(_BLOCKS) > 0, "No Sigil code blocks found in whitepaper"


def test_whitepaper_block_count() -> None:
    """Sanity check: whitepaper should have a substantial number of blocks."""
    # The spec calls for ~1100 lines with many examples
    assert len(_BLOCKS) >= 30, (
        f"Expected at least 30 Sigil blocks, found {len(_BLOCKS)}"
    )
