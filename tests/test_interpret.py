"""Sigil ⇄ natural-language interpreter tests (the human↔agent hinge)."""

from sigil_core import compact, parse_one
from sigil_core import interpret as I


def test_allocation_renders_english():
    m = I.build_allocation(
        sender="greyhound:int", receiver="ai:oxley",
        task_ref="docs/outstanding/oxley-btc-price-flap.md",
        task_title="BTC price flap guard", step="dev/implementation",
        rationale="owns oxley data", confidence=0.9,
    )
    names = {"greyhound:int": "Greyhound", "ai:oxley": "Oxley Agent"}
    en = I.to_locale(m, "en", names)
    # natural, conversational — earns human trust, not a form dump
    assert en == (
        "Greyhound suggests Oxley Agent take “BTC price flap guard” at the "
        "dev/implementation step, since owns oxley data (90% confident)."
    )
    # friendly names resolve; raw refs do not leak
    assert "greyhound:int" not in en


def test_round_trip_through_parser_is_stable():
    """Serialize → parse → render must equal render-of-original (wire is lossless)."""
    m = I.build_allocation(
        sender="greyhound:int", receiver="ai:oxley",
        task_ref="docs/outstanding/x.md", step="dev/review", confidence=0.75,
    )
    direct = I.to_locale(m, "en")
    reparsed = I.to_locale(parse_one(compact(m)), "en")
    assert direct == reparsed


def test_locale_swaps_the_verb_not_the_refs():
    m = I.build_allocation(sender="greyhound:int", receiver="ai:oxley",
                           task_ref="docs/outstanding/x.md")
    vi = I.to_locale(m, "vi")
    zh = I.to_locale(m, "zh")
    assert "đề xuất với" in vi          # localized verb
    assert "x.md" in vi                 # ref preserved verbatim
    assert "提议" in zh
    # unknown locale falls back to English verb, never crashes
    assert "proposes to" in I.to_locale(m, "xx")


def test_from_locale_carries_human_text_as_knowledge():
    m = I.from_locale("prioritize the hashrate feed",
                      sender="user:peter", receiver="ai:oxley")
    assert m.msg_type == "K"
    wire = compact(m)
    assert wire.startswith("[K ")
    assert "hashrate" in I.to_locale(parse_one(wire), "en")


def test_confidence_query_qualifier_is_silent():
    """prob:? (query confidence, -1) renders nothing rather than a bogus %."""
    m = I.build_allocation(sender="a:x", receiver="a:y",
                           task_ref="t", confidence=None)
    assert "%" not in I.to_locale(m, "en")
