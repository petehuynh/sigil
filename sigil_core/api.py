"""Sigil's door for a host (clean break P-SI-1 S3): outside Sigil, import the
language names from ``sigil_core`` (``parse``, ``serialize``, ``msg`` …) or
``sigil_core.api`` — check-module-boundaries ratchets any other reach. A host
mounts the landing through ``block()``. Importing this loads no Flask: the
landing is imported only when ``block()`` is called."""
from __future__ import annotations

from sigil_core.server import block

__all__ = ["block"]
