# ssz-z-python

Python bindings to [Lodestar's Zig SSZ engine](https://github.com/ChainSafe/lodestar)
for SSZ serialization, consensus JSON, and hash tree roots. Supports Electra,
Fulu, and Gloas with mainnet, minimal, and gnosis presets in the same process.

[UPSTREAM.json](UPSTREAM.json) is the source of native dependency revisions,
archive checksums, specification/API revisions, supported presets/forks, and
native ABI version. Native sources are downloaded unchanged, without patches.
Gloas schemas follow a draft specification and may change when the pin advances.
Gnosis uses Lodestar's preset constants; official Ethereum vectors cover mainnet
and minimal.

## Installation and development

Linux AMD64 or ARM64 and Python 3.12 or newer are required. Install from source
in your target environment:

```sh
uv pip install .
```

Source builds install the pinned Zig compiler through the build requirements,
then compile all presets with `ReleaseSafe` and a baseline CPU target. AMD64
also requires GNU binutils for the upstream assembly backend. No system Zig,
Node.js, or Rust is required. Builds download checksummed native archives over
HTTPS and cache their sources under `build/deps`. Populate that cache ahead of
time with `python tools/fetch_native.py` for offline reuse.

The installed package has no runtime Python dependencies. It includes native
libraries for the build machine's platform; portable public wheels are not
provided. Building inside your application's Docker image is supported.

```sh
uv sync --locked
uv run --locked pytest
uv run --locked mypy
uv run --locked pre-commit install
```

There is one `dev` dependency group. To run hooks without compiling the project:

```sh
uv sync --locked --only-group dev
uv run --no-sync pre-commit run --all-files --show-diff-on-failure
```

Run `uv sync --locked` again before using the library. Python-only edits are
live in editable installations. Python source and native build-input changes
invalidate uv’s build cache, including for non-editable installations. uv builds constrain the isolated setuptools version in `pyproject.toml`.

## Codecs and immutable values

```python
from ssz_z import get_type, list_types

codec = get_type("SignedBeaconBlock", fork="gloas", preset="mainnet")
value = codec.default()
serialized = value.to_ssz()
assert codec.load_ssz(serialized) == value
assert codec.load_json(value.to_json()) == value
assert codec.hash_tree_root_from_ssz(serialized) == value.hash_tree_root()

names = list_types(fork="fulu", preset="gnosis")
print(codec.schema)  # recursive Schema metadata reflected from Zig
```

`fork` and `preset` are required. Primitive types such as `Uint256` have their
own `fork="primitive"` namespace and can also be resolved from each consensus
fork. Names are case-sensitive.

Values retain validated, immutable SSZ bytes without materializing Python value
trees. `load_ssz` accepts bytes, bytearray, or memoryview and snapshots mutable
inputs. `load_json` accepts a complete UTF-8 JSON document as bytes or text.
`to_ssz()` and `to_json()` return bytes; send JSON bytes directly to an HTTP
client without encoding them again. To replace a value, load a new document.

Consensus JSON uses decimal strings for integers, JSON booleans, `0x` hex strings
for bytes and bits, arrays for other collections, and objects for containers.
Bitlists include the SSZ delimiter. Scalar inputs must also be JSON documents:
`codec.load_json('"0x01020304"')`, for example. Field order is arbitrary on input
and follows schema order on output. Duplicate/unknown/missing fields, invalid
lengths and bitfields, out-of-range integers, and malformed SSZ raise `SSZError`,
a `ValueError` subclass. Unknown type/fork/preset names raise `ValueError`.

Inputs and constructed SSZ outputs are limited to 512 MiB. JSON output can be
larger than SSZ input and has no separate size cap. Progressive collections have
no specification length bound.

`value.field("body.signed_execution_payload_bid.message.builder_index")` reads
a scalar or byte field from nested containers without native calls.
`value.sign(signature)` attaches an existing 96-byte signature when a compatible
`Signed<Type>` wrapper exists. It performs no BLS cryptography. When the unsigned root is cached,
signing cheaply derives and caches the signed root from it. Otherwise the signed
root is computed on its first request.

## Beacon API proposals

```python
from ssz_z.beacon_api import load_proposal_json, load_proposal_ssz

response = load_proposal_json(response_bytes, headers=response_headers, preset="mainnet")
proposal = response.proposal
# For an application/octet-stream response:
response = load_proposal_ssz(ssz_bytes, headers=response_headers, preset="mainnet")
```

Both loaders require `Eth-Consensus-Version`, plus
`Eth-Execution-Payload-Blinded` for Electra/Fulu or
`Eth-Execution-Payload-Included` for Gloas. JSON body metadata cannot replace
missing headers. Recognized metadata present in the body must match a header;
additional metadata is preserved. Response metadata is immutable, with block
values normalized to integers. Zig scans the response envelope; Python decodes
only its metadata. For an explicitly selected codec, `load_json(text, wrapped=True)`
extracts `data` without retaining metadata.

Electra/Fulu return a `BlockValue` adapter:

```python
proposal = response.proposal
header = proposal.header_dict()  # decimal/hex strings for signer APIs
root = proposal.block_hash_tree_root()  # unsigned block root
slot = proposal.slot
signed = proposal.sign(signature)
publication = signed.value.to_ssz()
```

You can also construct `BlockValue(codec.load_ssz(data))` directly. Its helpers
work with blocks, blinded blocks, and contents wrappers. Contents roots include
proofs/blobs; `block_hash_tree_root()` hashes only the unsigned block.

Electra/Fulu expose `BeaconBlockContents`, `SignedBeaconBlockContents`,
`BlindedBeaconBlockBody`, `BlindedBeaconBlock`, and `SignedBlindedBeaconBlock`.
Contents contain `block` (or `signed_block`), `kzg_proofs`, and `blobs`.
Fulu proof lists use the cell-proof SSZ bound. Relationships between proof,
blob, and commitment counts require caller-side consensus validation.

Gloas returns a `GloasProposal` adapter, separating block publication from
execution-payload revelation:

```python
proposal = response.proposal
root = proposal.block.block_hash_tree_root()
signed_block = proposal.sign_block(block_signature)
block_publication = signed_block.to_ssz()

if proposal.is_self_build and proposal.payload_included:
    signed_payload = proposal.sign_payload(payload_signature)
    payload_publication = signed_payload.to_ssz()
```

Gloas block publication uses a bare `SignedBeaconBlock`; there is no
`SignedBeaconBlockContents`. Publish the block before revealing its payload.
For stateful self-builds, fetch an `ExecutionPayloadEnvelope` from the producing
node and pass its `NativeValue` as `envelope=` to `sign_payload`. This returns
a bare signed envelope. Stateless contents preserve proofs/blobs in
`SignedExecutionPayloadEnvelopeContents`. The adapter checks the block root,
parent root, builder index, and slot against the proposal. Builder bids reject
`sign_payload()` because revelation belongs to the builder.

## Native architecture and builds

ctypes calls a small C ABI documented in [native/bindings.h](native/bindings.h).
Calls release the GIL and own independent arenas. Returned native buffers are
copied into Python and freed before returning; foreign pointers never outlive a
call. Concurrent first hashes are synchronized to initialize the upstream C
backend safely. Subsequent hashes run concurrently.

Validation, JSON conversion, and Merkleization execute in Zig. Header and body
root projections hash serialized bytes directly. Python handles scalar
projections and assembles signed wrappers from validated byte segments.
`to_ssz()` returns retained bytes; cached roots do not cross the native boundary.
Defaults are serialized directly to SSZ. The loader rejects mismatched native
ABI versions. Build provenance is copied into the installed package, so runtime
metadata never depends on a source checkout.

```sh
uv build
uv run --locked python -m ziglang build -Doptimize=ReleaseSafe -Dcpu=baseline
uv run --locked python -m ziglang fmt --check build.zig native
```

`uv build` builds an sdist and then a local platform wheel from that sdist.
`-Dpreset=minimal` selects one preset for direct Zig builds; `-Dpython=/path/to/python`
selects the dependency-fetch interpreter. Python packaging builds all presets
into the package independently of `zig-out`.

See [VALIDATION.md](VALIDATION.md) for vectors and schema regeneration, and the
[benchmark instructions](performance/report.md) for performance measurements.
