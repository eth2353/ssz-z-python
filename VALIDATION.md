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

Every normal test run checks GitHub for the newest published consensus-specs
release, including prereleases, and runs all its SSZ static vectors for mainnet
and minimal across the supported forks. Archives are checked against GitHub's
SHA-256 digests; extracted vectors are cached under ignored `fixtures/releases`.
The first download is large; subsequent runs reuse the extracted files. CI caches
these files by release asset IDs. Missing suites and download failures fail the
run instead of silently skipping vectors. Gnosis has local preset-specific tests.

The vector release deliberately floats independently of the pinned schemas.
Upstream schema changes may therefore fail tests until the bindings are updated.
The selected release and archive digests are recorded in the cache's `release.json`.
Set `GITHUB_TOKEN` to authenticate GitHub API requests if needed.

To prefetch the newest vectors:

```sh
python -m tools.fetch_vectors
```

For an offline rerun or reproduction of a specific release, set `SSZ_SPEC_TESTS`
to its extracted `tests` directory. All supported fork/preset suites must exist;
an empty or incomplete override is an error. This explicit override is the only
way to bypass the latest-release check.

Other tests cover default round trips for every exported codec, invalid SSZ and
JSON, concurrency, block projections, proposal metadata, and signed wrappers.

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
regenerate, and run the latest official vectors when upgrading.

## Packaging

CI runs on Linux AMD64 and ARM64 using the Python versions in
[the workflow](.github/workflows/test.yml). It tests an editable source build,
builds an sdist and a local wheel, and tests the installed wheel. These are
local build artifacts, not portable public wheels. Third-party notices ship
with distributions; dependency sources and prebuilt binaries are excluded from
the sdist. Record validation results from the current run rather than treating
historical test counts as coverage guarantees.
