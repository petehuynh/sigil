# Changelog

## 1.2.0 — 2026-10-12

- Sigil is a block (bojio clean break P-SI-1): the `/sigil` landing moves
  into the package as `sigil_core.server` behind a new `[web]` extra, with
  its templates and static; `sigil_core.api` is the host's door and
  `redwood.blocks: sigil` the entry point; an empty `migrations/` dir.
- `sigil serve` (`sigil_core.standalone`): the landing alone, plain Flask.
- The language is unchanged: no new dependency, same parser output.
  `sigil_core.PARSER_TESTS` publishes the parser suite's size (303), the
  number Aetheria quotes, checked by `repo_tests/test_parser_count.py`.
- Home moves to `petehuynh/sigil` (P-SI-3); the old repo content is tagged
  `pre-clean-break-2026-10`.

## 1.1.0

- The language as the bojio monorepo carried it in `packages/sigil-core`.
