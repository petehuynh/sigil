# Sigil's own migrations (clean break P-SI-1 S2)

db-core reads this directory as block `sigil` (`tree_block_dirs`: a
`packages/<name>-core/<name>_core/migrations/` dir is block `<name>`'s).
It is **empty on purpose**: Sigil owns no table. `schema_version_sigil` is
created by db-core the first time a migration here is recorded.

`193_sigil_advertised_features.sql` stays in `app/migrations/` because it
writes a HOST table (`feature_access`) — the same rule that kept LYD's and
BitTontine's host-table migrations the host's. The brand/plan seeds that
name Sigil among other brands (168, 169, 170, 198, 205, 206, 218, 268, 306)
are host migrations too.

A table of Sigil's own (`sigil_*`) is created HERE, never in
`app/migrations/` — `app/tests/test_sigil_migrations_are_the_blocks.py`
fails the gate otherwise.
