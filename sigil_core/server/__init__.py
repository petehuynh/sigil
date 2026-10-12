"""Sigil's server side — the ``/sigil`` landing blueprint (clean break P-SI-1
S1, spec docs/specs/feature-p-si1-slice-plan-2026-10-12-1700.md).

Moved here from the two copies in ``app/app.py`` and ``app/app_https.py``.
This subpackage needs the ``[web]`` extra (Flask); ``import sigil_core`` — the
language every Aetheria node and the A2A path parse with — never imports it,
so the language stays dependency-free.

``block()`` is the entry point (``redwood.blocks`` group, ``sigil``): it names
what the host mounts, imported lazily so reading the entry point loads
nothing.
"""
from __future__ import annotations

__all__ = ["block"]


def block() -> dict:
    """What a Redwood host mounts for Sigil."""
    import os

    from .landing import bp

    return {
        "name": "sigil",
        "blueprint": bp,
        # the block's own migrations dir, applied by Redwood db-core (P-SI-1 S2);
        # empty today — Sigil owns no table
        "migrations": os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations"),
    }
