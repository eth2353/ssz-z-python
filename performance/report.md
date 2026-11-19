# Sampled performance comparison

These are preliminary results from **8 evenly spaced real blocks per network,
one timed pass**, collected on macOS arm64 with Python 3.12.9. The user requested
no full benchmark. These measurements do not establish corpus-wide averages or
tail latency. The saved aggregate is [pilot-summary.json](pilot-summary.json). These samples
predate later API simplifications; the harness and examples use the current API.

The comparison uses the same process, interpreter and inputs for the optimized
SSZ-backed API and spy-ssz commit
`612c3f73c54ff2a8cbc374f5c4af7b9d7aa24d00`. The optimized source was developed
from bindings commit `604b60a4cd11971e1848744f8e527bae3f68b948`; the saved
summary records the Python source hashes. Its installed distribution metadata
still reported 0.1.0; the implementation became release 0.2.0.

## Proposal flow

Decode an unsigned production response, obtain its header, attach the existing
signature, encode publication bytes, and obtain the unsigned block root.
Times are arithmetic means in milliseconds per sampled block; smaller is better.

| Network / fork | Wire format | spy-ssz | SSZ-backed bindings | Speedup |
| --- | --- | ---: | ---: | ---: |
| mainnet / Fulu | SSZ | 2.8582 | 0.7087 | 4.03x |
| mainnet / Fulu | JSON | 3.6100 | 1.9364 | 1.86x |
| Hoodi / Fulu | SSZ | 0.4887 | 0.1177 | 4.15x |
| Hoodi / Fulu | JSON | 0.8066 | 0.4508 | 1.79x |
| Gloas / mainnet preset | SSZ | 0.0815 | 0.0388 | 2.10x |
| Gloas / mainnet preset | JSON | 0.1534 | 0.1093 | 1.40x |

Fulu production contents use empty blob/proof lists because the saved corpus
contains blocks without those publication attachments. Blob-bearing contents
are covered separately by correctness tests; their timing is not represented
here. No Electra, minimal or gnosis timing claims are made.

## Individual operations

Mainnet Fulu samples, milliseconds per block:

| Operation | spy-ssz | SSZ-backed bindings |
| --- | ---: | ---: |
| JSON decode | 0.5139 | 0.9433 |
| JSON encode | 0.3094 | 0.2940 |
| SSZ decode / validation | 0.0156 | 0.0050 |
| SSZ encode / retained bytes | 0.0172 | 0.0003 |
| Object to root, first call | 2.6941 | 0.7003 |
| SSZ to root | 2.7035 | 0.6939 |

SSZ-backed values retain validated immutable SSZ. Returning those bytes does
not serialize a Python object, so the SSZ encode measurement is a buffer
retrieval. The old API also returns an opaque value; both implementations are
checked for equivalent publication bytes, JSON values, headers and roots outside
the timed callbacks. JSON decoding remains slower than spy-ssz in these samples
(1.84x on mainnet, 1.70x on Hoodi, 1.36x on Gloas).

The former dictionary API materialized Python trees. A separate 25-cycle profile
of `from_json -> serialize -> deserialize -> to_json` on one mainnet block
dropped from 0.626 s / 150 native operations to 0.161 s / 50 operations.
See [baseline-profile.txt](baseline-profile.txt) and
[optimized-profile.txt](optimized-profile.txt). These profiles describe one
block and are separate from the comparison above.

## Integration

```python
from ssz_z import get_type
from ssz_z.beacon_api import BlockValue

codec = get_type("BeaconBlockContents", fork="fulu", preset="mainnet")
proposal = BlockValue(codec.load_ssz(response_bytes))
header = proposal.header_dict()  # consensus JSON strings for signer APIs
root_bytes = proposal.block_hash_tree_root()
slot = proposal.slot
signed = proposal.sign(signature)
publication = signed.value.to_ssz()
```

Use `load_json(response_bytes, wrapped=True)` for a REST response with a `data`
field. `NativeValue.to_json()` produces wire JSON bytes. `block_hash_tree_root()`
returns 32 bytes; use `"0x" + root_bytes.hex()` when an API expects hex.
Gloas uses `BeaconBlock` for production and exposes `.builder_index`.

The SSZ proposal flow performs validation and one combined header/body-root
projection in native code. It caches the header and block root, reads scalar
fields directly from validated bytes, and attaches signatures with one buffer
allocation. It performs no BLS signing. Metadata resolution is cached separately.
Values own immutable Python bytes and use ordinary garbage collection. Returned
publication bytes remain valid independently of their source value. Python code
and native libraries are installed together; the loader verifies the native ABI recorded in UPSTREAM.json,
documented in
[native/bindings.h](../native/bindings.h).

## Reproduction

[benchmark.py](benchmark.py) accepts the saved corpus and an isolated installation
of the exact old spy-ssz pin. It never imports Vero or changes either checkout.
Point `--spy-site-packages` at the preserved old build. For a similarly limited pilot:

```sh
PYTHONPATH=src /path/to/python performance/benchmark.py \
  --corpus /path/to/real-blocks \
  --spy-site-packages /path/to/pinned-spy/site-packages \
  --output /tmp/ssz-z-pilot --limit 8 --rounds 1
```

Inputs are loaded into RAM and SHA-256 checked before timing. The harness warms
up at most 12 blocks per network (8 in this pilot), alternates library order by
block/pass, disables garbage collection during the measured loop, and checks
outputs outside individual timers. It saves raw samples, aggregate statistics,
interpreter/platform metadata, source hashes and native library hashes. The harness now exercises only the wire API; the dictionary profile above is
historical and describes an API that has since been removed. The committed pilot summary retains
the metadata available at the time; later harness additions record more hashes.

The full correctness suite passed **24,247 tests**, including 24,064 distinct
official beta.4 cases. This validation is independent of performance sampling;
see [VALIDATION.md](../VALIDATION.md).
