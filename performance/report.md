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

## Results

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
