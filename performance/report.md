# Performance comparison

Rerun on November 19, 2026 after the audit changes, using **all 296 paired
Fulu blocks** in `/tmp/beacon_blocks` (slots 13689000–13689300, with gaps).
The inputs total 106,253,470 JSON bytes and 52,978,975 SSZ bytes.

The comparison uses Python 3.12.16 on macOS 26.7.1 arm64, with both libraries
in the same process. The baseline is spy-ssz commit
`612c3f73c54ff2a8cbc374f5c4af7b9d7aa24d00`; current bindings and harness are at
`6712370cfcaae2365a8673a3ce7366e2df46ebbe`. This compares the current bindings
with spy-ssz, rather than measuring the audit changes against the previous
bindings implementation.

The [saved summary](beacon-blocks-summary.json) contains per-pass means,
percentiles, input hashes, source/native hashes, and interpreter provenance.
Raw samples and metadata are retained locally in
`performance/results/2026-11-19-beacon-blocks/`.

## Direct comparison with pre-audit ssz-z-python

A separate run compares revision `5788045` (immediately before the audit changes)
against the post-audit implementation, with the direct comparison harness at
`f2b4ab3`. Both revisions were built using Zig 0.16.0, `ReleaseSafe`, and baseline
CPU settings, with identical native dependency pins. Both Python packages and
their separate native libraries were loaded into one process on the same
Python 3.12.16 interpreter. Library order alternated by block and pass.

All 296 Fulu blocks were processed three times, after 12 warmups. All output,
root, header, and signing equivalence checks passed. Defaults were measured
separately with 10 calls per type per pass, checking identical default SSZ bytes.
The [before/after summary](before-after-summary.json) records the measurements,
input digests, and both packages' Python/native hashes. Raw samples are under
`performance/results/2026-11-19-before-after/`.

Milliseconds per operation, median of three pass means; negative change means
less time. Default rows measure construction plus retrieval of the default SSZ.

| Operation | Before audit | After audit | Time change |
| --- | ---: | ---: | ---: |
| JSON decode | 1.09470 | 1.12672 | +2.9% |
| JSON encode | 0.39378 | 0.39348 | -0.1% |
| SSZ decode / validation | 0.00657 | 0.00667 | +1.6% |
| Value to root | 0.76983 | 0.77295 | +0.4% |
| SSZ to root | 0.77053 | 0.76558 | -0.6% |
| Proposal flow, JSON | 2.31493 | 2.31784 | +0.1% |
| Proposal flow, SSZ | 0.80157 | 0.81413 | +1.6% |
| Default BeaconBlock | 0.02428 | 0.00882 | -63.7% |
| Default SignedBeaconBlock | 0.02390 | 0.00820 | -65.7% |
| Default BeaconState | 21.81855 | 0.88383 | -95.9% |
| Sign an already-hashed bare block | 0.02238 | 0.01251 | -44.1% |
| Retrieve signed root after signing | 0.00018 | 0.77037 | +428864.7% |
| Sign + retrieve signed root, combined | 0.02255 | 0.78308 | +3372.3% |

The ordinary proposal flow is essentially unchanged in this run (+0.1% for
JSON, +1.6% for SSZ). JSON decoding measured +2.9%; these small differences from
one three-pass run should not be treated as precise regression estimates.
Direct default SSZ is the clear gain: block defaults are about 2.8–2.9× faster,
and state defaults about 24.7× faster.

**Follow-up:** cached signed-root derivation has since been restored. The table
above records the intermediate implementation before that restoration.

The measured signing tradeoff was substantial when a caller requested the
**signed** root after already hashing the unsigned block. Before the audit,
`sign()` cheaply derived and cached that root from the cached unsigned root.
In that measured revision, `sign()` left the signed root empty, and its first request performed native
hashing of the signed value. The combined row sums paired sign/root timings
before aggregating, so it includes work formerly performed inside `sign()`.
This differs from the normal proposal flow, which requests the **unsigned**
block root and does not hash the signed publication.

Reproduce after preparing the pre-audit source snapshot and its native libraries:

```sh
.venv/bin/python performance/compare_revisions.py \
  --before-source build/before-audit-5788045 --before-revision 5788045 \
  --before-dependencies build/benchmark-spy-env/lib/python3.12/site-packages \
  --corpus /tmp/beacon_blocks \
  --output performance/results/2026-11-19-before-after --rounds 3
```

The dependency path supplies the pre-audit version's `msgspec`; it does not
replace either bindings implementation. The isolated snapshot was extracted
from `git archive 5788045` and built without modifying the working checkout.

## Comparison with spy-ssz

Times are milliseconds per block, reported as the **median of three pass means**;
each pass processes every block. Comparisons use the unrounded measurements.

| Operation | spy-ssz | Current bindings | Current relative to spy-ssz |
| --- | ---: | ---: | ---: |
| JSON decode | 0.62434 | 1.11528 | 1.79× slower |
| JSON encode | 0.36118 | 0.40324 | 1.12× slower |
| SSZ decode / validation | 0.01984 | 0.00647 | 3.07× faster |
| SSZ encode / retained bytes | 0.02069 | 0.00013 | 161.17× faster |
| Value to root, first call | 2.97946 | 0.77596 | 3.84× faster |
| SSZ to root | 3.02748 | 0.76982 | 3.93× faster |
| Proposal flow, JSON | 4.13744 | 2.32759 | 1.78× faster |
| Proposal flow, SSZ | 3.16100 | 0.80813 | 3.91× faster |

SSZ output retrieves retained bytes in the current bindings; its encode result
is buffer retrieval, rather than fresh serialization of an object.
Root measurements use the first request on a freshly loaded value.
Standalone JSON decoding remains slower than spy-ssz; the combined proposal
flow benefits from faster hashing and byte-backed projection/signing.

The proposal flow loads an unsigned production response, derives its header,
attaches the existing signature, encodes publication bytes, and obtains the
unsigned block root. Fulu contents are constructed from the corpus's blocks
with **empty proof/blob lists**, because the corpus does not contain these
publication attachments. This measures the codec/BlockValue path, excluding
HTTP response-header metadata processing and BLS cryptography. The new default
serialization operation is also outside this benchmark's measured workload.

These results cover this Fulu corpus and the mainnet preset. They do not measure
Electra, Gloas, other presets, or populated blob/proof publication contents.
The [previous pilot](pilot-summary.json) used eight blocks per network and a
different interpreter/source snapshot, so its timings are not a controlled
before/after comparison with this run.

## Method and correctness

The harness preloads the paired files, records SHA-256 input digests, warms up
12 evenly spaced blocks, and disables Python GC during measured passes.
Library order alternates by block and pass. Preparation, result validation,
and CSV output are outside individual operation timers.

All 888 timed block/pass pairs passed the equivalence checks: original SSZ
bytes, signed roots, emitted JSON values, headers, unsigned block roots, and
signed publication JSON/SSZ. There are 14,208 timed samples
(296 blocks × 3 passes × 2 libraries × 8 operations).

## Reproduction

Create or select an isolated installation of the exact spy-ssz baseline above,
then run with the bindings' interpreter:

```sh
.venv/bin/python performance/benchmark.py \
  --corpus /tmp/beacon_blocks \
  --spy-site-packages build/benchmark-spy-env/lib/python3.12/site-packages \
  --output performance/results/2026-11-19-beacon-blocks --rounds 3
```

The harness supports both flat `json/` and `ssz/` directories and the older
network-directory manifests. Its output includes `samples.csv`, `metadata.json`,
and `summary.json`. The original files and baseline installation are read-only
inputs to the benchmark.
