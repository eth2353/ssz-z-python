# Audit follow-up

The audit and implementation were performed on November 19, 2026.

Decisions:

- Retain ctypes, immutable validated SSZ bytes, and per-call native ownership.
- Protect upstream hashtree's first-use backend selection with a native atomic
  initialization barrier. The underlying fix belongs in hashtree C (or its
  hashtree-z wrapper); this repository does not patch downloaded dependencies.
- Retain bounded inputs and constructed SSZ; allow larger JSON output.
- Build from source in the target environment; portable public wheels are out
  of scope.
- Keep one dev dependency group.

Implemented improvements include isolated build constraints, native-only cache
invalidation, hooks without project installation, lazy signed roots, direct
default SSZ, removal of msgspec, public type checking, and manifest-based
provenance. The schema generator rejects mismatched or edited specification
checkouts.

[README.md](README.md) describes the current behavior;
[VALIDATION.md](VALIDATION.md) contains validation and regeneration commands;
[UPSTREAM.json](UPSTREAM.json) owns dependency and ABI metadata.
