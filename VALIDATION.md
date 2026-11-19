# Validation and schema maintenance

Use [UPSTREAM.json](UPSTREAM.json) for the authoritative engine, specification,
Beacon API, and hashing dependency pins. `native/consensus.zig` is generated from
the pinned specification using Python AST parsing; specification code is never
executed. The native engine is not patched.

## Tests

```sh
uv sync --locked
uv run --locked pytest
uv run --locked mypy
uv run --locked python -m ziglang fmt --check build.zig native
uv run --locked pre-commit run --all-files --show-diff-on-failure
```

The normal suite includes bundled official SSZ vectors, default round trips for
all exported codecs, scalar/collection boundaries, invalid SSZ and JSON,
concurrent reads and cold-start hashes, block projections, proposal metadata,
and signed publication wrappers. Official vectors compare independently
published values, bytes, and roots. Gnosis has local preset-specific coverage;
the Ethereum release does not publish gnosis vectors.

For the full official static suites, download `mainnet.tar.gz` and
`minimal.tar.gz` from the consensus-specs release identified by the manifest.
Extract them with:

```sh
python tools/extract_vectors.py /path/to/minimal.tar.gz fixtures
python tools/extract_vectors.py /path/to/mainnet.tar.gz fixtures
uv run --locked pytest -m spec
```

`--cases-per-suite 2` limits extraction to a sample. `SSZ_SPEC_TESTS=/path/to/tests`
selects another extracted suite. Extraction records the archive digest; verify
it against the release asset before relying on external vectors. The bundled
vector manifest records the provenance of committed cases.

## Regenerate schemas

Check out the consensus-specs commit from `UPSTREAM.json`, with no edits or
untracked files under `specs`. Populate the pinned engine sources, then run:

```sh
python tools/fetch_native.py
python tools/generate_schemas.py /path/to/consensus-specs native/consensus.zig
uv run --locked python -m ziglang fmt native/consensus.zig
git diff -- native/consensus.zig
```

The generator verifies the specification revision and source cleanliness before
writing output. It uses the cached Lodestar sources by default;
`--lodestar-root /path/to/lodestar` overrides that location. Update upstream pins,
regenerate, and run the matching official vectors together when upgrading.

## Packaging

CI runs on Linux AMD64 and ARM64 using the Python versions in
[the workflow](.github/workflows/test.yml). It tests an editable source build,
builds an sdist and a local wheel, and tests the installed wheel. These are
local build artifacts, not portable public wheels. Third-party notices ship
with distributions; dependency sources and prebuilt binaries are excluded from
the sdist. Record validation results from the current run rather than treating
historical test counts as coverage guarantees.
