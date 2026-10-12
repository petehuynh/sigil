# sigil-core

Sigil — the formal language for AI-to-AI communication — and its landing.

Version: **1.2.0**

Since clean break P-SI-3 this repo (`petehuynh/sigil`) is Sigil's home: the
bojio monorepo no longer carries it and installs it by tag —

    sigil-core @ git+https://github.com/petehuynh/sigil.git@v1.2.0

The content this repo held before (an older sigil-core, `b24f339`) is kept
at the tag `pre-clean-break-2026-10`.

## The language

    pip install sigil-core

`import sigil_core` needs only the Python standard library: parse, build,
serialize and interpret Sigil messages. Every Aetheria node parses its feed
with it, so it never pulls a web framework.

    from sigil_core import parse_one, serialize
    node = parse_one('[Q grok-1 user:42 ask:weather @loc:singapore "tomorrow" prob:?]')
    print(serialize(node))

## The landing, alone

    pip install 'sigil-core[web]'
    sigil serve                 # http://127.0.0.1:5307/ -> /sigil

`sigil serve` is Sigil's landing with nothing else: `/sigil`, `/sigil/spec`,
`/sigil/docs`, `/health`. Sigil owns no table, no API and no panel, so there
is no store and no Redwood.

Inside the bojio monorepo the landing blueprint mounts beside every other
block (entry point `redwood.blocks: sigil`). Other blocks import Sigil
through its language names (`from sigil_core import parse`) or
`sigil_core.api`; Sigil imports Flask (landing only), the standard library
and itself.

## Tests

    python -m pytest tests -q          # the language (the parser's suite)
    python -m pytest repo_tests -q     # the landing, `sigil serve` ([web]) and the count

The two suites are kept apart on purpose: Aetheria quotes the parser's test
count (`sigil_core.PARSER_TESTS`, checked by `repo_tests/test_parser_count.py`),
and the landing's tests are not the parser's.
