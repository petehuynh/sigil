"""The ``/sigil`` landing pages — one blueprint, mounted by every host app."""
from __future__ import annotations

import os

from flask import Blueprint, render_template

_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# template_folder: the block's own copy. A host whose app-level loader also
# finds `sigil/…` (the monolith keeps a symlink to this one copy) resolves the
# same file either way.
bp = Blueprint("sigil", __name__, template_folder=os.path.join(_PKG, "templates"))


@bp.route("/sigil")
@bp.route("/sigil/")
def home():
    return render_template("sigil/home.html")


@bp.route("/sigil/spec")
def spec():
    return render_template("sigil/spec.html")


@bp.route("/sigil/docs")
def docs():
    return render_template("sigil/docs.html")
