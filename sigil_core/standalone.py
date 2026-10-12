"""``sigil serve`` — Sigil alone: its landing, nothing from any other block
(clean break P-SI-1 S4, spec docs/specs/feature-p-si1-slice-plan-2026-10-12-1700.md).

A host mounts Sigil's landing blueprint and fills its templates' ``brand``
and ``asset_v`` from its own context processor. Here Sigil is the host, so it
brings both: the portfolio's public domains (Sigil's own links relative,
``/sigil``) and its own package version as the cache-buster. Sigil owns no
table, no API and no panel, so this is plain Flask and the block's own files —
no store, no Redwood. Needs the ``[web]`` extra.

  /                   302 to /sigil
  /sigil, /sigil/...  the landing pages (sigil_core.server.landing)
  /static/...         the landing's own static (sigil/, shared/theme-auto.*)
  /health             {"ok": true, "block": "sigil"}
"""
from __future__ import annotations

import argparse
import os
import sys

__all__ = ["BRAND_URLS", "create_app", "main"]

_PKG = os.path.dirname(os.path.abspath(__file__))

#: The monolith's BRAND_URLS_PROD, with Sigil's own links on this host.
BRAND_URLS = {
    "bojio": "https://bojio.net",
    "aether": "https://goaether.net",
    "aetheria": "https://aetheria.top",
    "albatross": "https://albatrossdesk.com",
    "bittontine": "https://bittontine.com",
    "gilstead": "https://gilstead.xyz",
    "greyhound": "https://getgreyhound.com",
    "lyd": "https://littleyellowdragon.com",
    "oxley": "https://oxleydata.com",
    "sigil": "/sigil",
    "wallclip": "https://wallclip.net",
    "scute": "https://usescute.com",
}


def _asset_version() -> str:
    try:
        from importlib.metadata import version
        return version("sigil-core")
    except Exception:
        return "0"


def create_app():
    """A Flask app serving Sigil alone."""
    from flask import Flask, jsonify, redirect

    from .api import block

    app = Flask("sigil", root_path=_PKG, static_folder=os.path.join(_PKG, "static"),
                static_url_path="/static")
    app.register_blueprint(block()["blueprint"])

    @app.context_processor
    def _sigil_context():
        return {"brand": BRAND_URLS, "asset_v": _asset_version()}

    @app.get("/")
    def _home():
        return redirect("/sigil", code=302)

    @app.get("/health")
    def _health():
        return jsonify({"ok": True, "block": "sigil"})

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sigil", description="Sigil, standalone")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="serve Sigil's landing alone")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=int(os.environ.get("SIGIL_PORT", "5307")))
    args = parser.parse_args(argv)
    app = create_app()
    print(f"sigil: serving on http://{args.host}:{args.port}/", file=sys.stderr)
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
