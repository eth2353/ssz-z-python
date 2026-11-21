# Performance measurements

Run benchmarks on a supported Linux or macOS system. Record the CPU,
Python version, source revisions, and build options with each result.
The harness records source/native hashes and input digests automatically.

Install the spy-ssz baseline in a separate environment, then run:

```sh
uv run --locked python performance/benchmark.py \
  --corpus /path/to/beacon_blocks \
  --spy-site-packages /path/to/spy-env/lib/python3.12/site-packages \
  --output performance/results/current --rounds 3
```

The corpus contains paired Beacon API JSON and SSZ files in `json/` and `ssz/`
directories. The harness also supports network-directory manifests. It writes
`samples.csv`, `metadata.json`, and `summary.json` under the output directory.

For comparisons between binding revisions, run
`uv run --locked python performance/compare_revisions.py --help`. Build both revisions with identical Zig, optimization, and CPU options.

The harness warms up inputs, alternates library order, disables Python GC while
timing, and validates equivalence outside operation timers. Root measurements
use fresh values, while SSZ output measures retrieval of retained bytes.
Proposal timings use empty proof/blob lists and exclude HTTP header metadata
processing and BLS cryptography. They do not measure large blob-bearing REST
responses; benchmark those separately before changing response decoding paths.

Generated results belong under ignored `performance/results/`. Historical
measurements remain available in Git history.
