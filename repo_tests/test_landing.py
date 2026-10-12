"""The landing and ``sigil serve``, from this package alone (bojio clean break
P-SI-3 S1). Paths are read relative to the package, so the suite runs the
same in petehuynh/sigil as in the bojio monorepo. Needs the ``[web]`` extra.

Kept out of ``tests/`` on purpose: that is the parser's suite, whose count
(``sigil_core.PARSER_TESTS``) Aetheria quotes.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
PAGES = ["/sigil", "/sigil/", "/sigil/spec", "/sigil/docs"]


def _client():
    sys.path.insert(0, str(PKG))
    from sigil_core.standalone import create_app
    return create_app().test_client()


def test_every_page_and_every_static_link_answers_alone():
    c = _client()
    links = set()
    for p in PAGES:
        r = c.get(p)
        assert r.status_code == 200 and b"<html" in r.data.lower(), p
        links |= set(re.findall(r'(?:href|src)="(/static/[^"?]+)', r.get_data(as_text=True)))
    assert "/static/sigil/tokens.css" in links and "/static/shared/theme-auto.js" in links
    bad = {u: c.get(u).status_code for u in links if c.get(u).status_code != 200}
    assert not bad, bad


def test_health_root_and_a_missing_file():
    c = _client()
    assert c.get("/health").get_json() == {"ok": True, "block": "sigil"}
    r = c.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/sigil")
    assert c.get("/static/sigil/no-such-file.css").status_code == 404


def test_the_block_names_its_blueprint_and_migrations():
    sys.path.insert(0, str(PKG))
    from sigil_core.api import block
    b = block()
    assert b["name"] == "sigil"
    assert Path(b["migrations"]).resolve() == (PKG / "sigil_core" / "migrations").resolve()
    assert b["blueprint"].name == "sigil"


def _flask_loaded_by(module: str) -> str:
    out = subprocess.run([sys.executable, "-I", "-c",
                          f"import sys; sys.path.insert(0, {str(PKG)!r}); import {module}; "
                          "print('flask' in sys.modules)"],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def test_the_language_loads_no_flask():
    assert _flask_loaded_by("sigil_core") == "False"
    # the probe can see Flask: the landing does load it
    assert _flask_loaded_by("sigil_core.server.landing") == "True"
