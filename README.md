# ssz-z-python

Native Python bindings to [ChainSafe Lodestar-Z](https://github.com/ChainSafe/lodestar-z)
for SSZ serialization, deserialization, consensus JSON, and hash tree roots.
Supports **Electra, Fulu, and Gloas**, each with **mainnet, minimal, and gnosis** presets.
All three presets can be used in the same Python process.

Lodestar-Z's active branch is `main`; the repository has no `master` branch.
This package vendors its latest `main` revision at the start of implementation,
`ba4f89e967bdb498f1d856f699f1ba2b863be330`. Exact source revisions and licenses
are recorded in [vendor/UPSTREAM.json](vendor/UPSTREAM.json).

## Install

```sh
python -m pip install .
```

Python 3.10 or newer is required. Source builds install Zig **0.16.0** through the
`ziglang` build dependency and compile three shared libraries in `ReleaseSafe`
mode with a baseline CPU target. No system Zig installation, Node.js, Rust, or
network access from Zig is required. Vendored source includes the SSZ engine,
SHA-256 wrapper, and native hashtree dependency. Linux x86 builds also need a
system assembler (GNU binutils), as required by the upstream assembly backend.

A built wheel has no Python runtime dependencies and requires no compiler.
The wheel contains native code and is specific to its operating system and CPU
architecture; its C ABI is independent of the CPython version.

For development:

```sh
python -m pip install -e '.[test]'
python -m pytest
```

## Use

```python
from ssz_z import get_type

block = get_type("SignedBeaconBlock", fork="gloas", preset="mainnet")

# Python values are dictionaries, lists, integers, bytes, and booleans.
value = block.default()
value["message"]["slot"] = 123

serialized = block.serialize(value)                 # bytes
restored = block.deserialize(serialized)            # dict
root = block.hash_tree_root(value)                  # 32 bytes
assert restored == value
assert block.hash_tree_root_from_ssz(serialized) == root

json_value = block.to_json(value)                   # JSON-compatible dict
json_text = block.dumps(value)                      # JSON text
assert json_value["message"]["slot"] == "123"
assert block.from_json(json_value) == value
assert block.loads(json_text) == value
```

Select any exported upstream type by its case-sensitive name:

```python
from ssz_z import list_types

names = list_types(fork="fulu", preset="gnosis")
state = get_type("BeaconState", fork="fulu", preset="gnosis")
attestation = get_type("Attestation", fork="electra", preset="minimal")
bid = get_type("ExecutionPayloadBid", fork="gloas", preset="mainnet")
uint256 = get_type("Uint256")  # primitives are available through every fork
print(attestation.schema)      # metadata reflected from the actual Zig type
```

Defaults are `fork="gloas"`, `preset="mainnet"`. `list_types` includes inherited
consensus types; primitive types have their own `fork="primitive"` namespace and
are also resolved by `get_type` from every fork. `encode`/`decode` are aliases
for `serialize`/`deserialize`.

| SSZ value | Python representation | Consensus JSON |
| --- | --- | --- |
| Container | `dict`, with snake_case field names | Object |
| Uint | Arbitrary precision `int` | Decimal string |
| Boolean | `bool` | Boolean |
| Byte vector/list | `bytes` | `0x`-prefixed hex |
| Bitvector | Packed `bytes`, least significant bit first | `0x`-prefixed hex |
| Bitlist | Packed `bytes`, **including the SSZ delimiter bit** | `0x`-prefixed hex |
| Other vector/list | `list` | Array |

`from_json` accepts a decoded JSON value or JSON text. Decimal strings and hex
strings are also accepted directly for scalar types. Serialization accepts both
the Python and consensus JSON representations. Input field order is irrelevant;
output follows schema order. Missing/unknown fields, duplicate JSON keys,
out-of-range integers, invalid lengths, noncanonical bitfields, and malformed SSZ
raise `ssz_z.SSZError` (a `ValueError` subclass). Unknown type/fork/preset names
raise `ValueError`. Progressive collections have no SSZ length limit; the binding caps inputs and
serialized outputs at 512 MiB.

## Fast path for blocks and other immutable values

`load_ssz`, `load_json`, and `load_obj` return an immutable `NativeValue` instead
of materializing a Python tree. Existing dictionary APIs retain their return
values and remain useful for editing small objects.

```python
proposal_type = get_type("BeaconBlockContents", fork="fulu", preset="mainnet")
with proposal_type.load_ssz(response_bytes) as proposal:
    header = proposal.header_dict()               # consensus JSON header
    block_root = proposal.block_hash_tree_root()  # 32-byte unsigned block root
    slot = proposal.slot                         # scalar projection, no native call
    with proposal.sign(signature) as signed:      # attach an existing 96-byte BLS signature
        publication_bytes = signed.to_ssz()      # immutable bytes, no additional copy
# publication_bytes remains valid after both values close
```

For JSON production responses, use
`proposal_type.load_json(response_bytes, wrapped=True)` to parse the REST
`data` field directly in Zig. For a bare JSON value, omit `wrapped=True`.
`signed.to_json()` returns **wire JSON bytes**; pass those bytes to the HTTP
client directly rather than JSON-encoding them again.

The SSZ path above performs two native operations: validate the input and
project/hash the block body. The header and unsigned block root are computed
together and cached. Signing copies the encoded bytes once into their signed
wrapper, preserving proof/blob bytes; it performs no BLS cryptography.
`to_ssz()` and cached roots do not cross the native boundary. Type metadata is
resolved on first use and cached separately.

`NativeValue.hash_tree_root()` hashes the complete value, including any
contents/signed envelope; `block_hash_tree_root()` specifically hashes the
unsigned block. `header_dict()` returns decimal/hex strings for signer APIs.
`field("body.signed_execution_payload_bid.message.builder_index")` projects a
scalar/byte field from nested containers without decoding the full object.
Gloas block/envelope values also expose `.builder_index`.

Values own Python-managed immutable SSZ buffers; no foreign pointers or native
arenas outlive a call. Each value serializes its operations with a lock, and
`close()` is idempotent and waits for in-flight operations. Independent values
can execute native operations concurrently with the GIL released. Context
managers release buffers early; ordinary Python garbage collection is also
sufficient. `to_obj()` creates an independent editable Python tree, while
`to_json_value()` creates a JSON-compatible tree. Construct a replacement with
`codec.load_obj(edited_value)` after editing.

See [performance/report.md](performance/report.md) for the sampled real-block
comparison, reproduction commands, and remaining JSON/dictionary costs.

## Beacon API block production and publishing

Electra and Fulu also expose `BeaconBlockContents`, `SignedBeaconBlockContents`,
`BlindedBeaconBlockBody`, `BlindedBeaconBlock`, and `SignedBlindedBeaconBlock`
for every preset. These use the current Beacon API wire fields:

```python
contents = get_type("BeaconBlockContents", fork="fulu", preset="mainnet")
value = contents.default()  # {"block": ..., "kzg_proofs": [], "blobs": []}
encoded = contents.serialize(value)
assert contents.deserialize(encoded) == value
```

Signed contents use `signed_block` instead of `block`. Blinded bodies replace
`execution_payload` with `execution_payload_header`, preserving field order and
all other body fields. A header containing the full payload's transaction and
withdrawal roots produces the same body and block roots as the full block.

The contents SSZ root includes the proofs and blobs. To obtain the block root
for signing, hash the contained `BeaconBlock` rather than the contents envelope.
Electra's proof list is bounded by `MAX_BLOB_COMMITMENTS_PER_BLOCK`; Fulu's cell
proof list uses `FIELD_ELEMENTS_PER_EXT_BLOB * MAX_BLOB_COMMITMENTS_PER_BLOCK`
(33,554,432). These are SSZ type bounds; validating relationships between blob,
commitment, and proof counts belongs to the caller's consensus validation.

Schemas follow [ethereum/beacon-APIs](https://github.com/ethereum/beacon-APIs/tree/01e99a6530b22941f619bde525cbf8bb61991d42),
with the revision recorded in `vendor/UPSTREAM.json` and implementation in
[native/beacon_api.zig](native/beacon_api.zig).

## Specification compatibility

The SSZ algorithms come from Lodestar-Z's latest pinned `main`. Consensus schemas
are generated from **consensus-specs v1.7.0-beta.4** by
[tools/generate_schemas.py](tools/generate_schemas.py), using only Python syntax
parsing. No specification code runs during generation. The generated
[native/consensus.zig](native/consensus.zig) uses the upstream engine for:

- Standard SSZ types for Electra and Fulu, including missing P2P containers.
- Gloas progressive containers, progressive lists, and progressive bitlists
  introduced by EIP-7688. These have different hash tree roots from ordinary SSZ.
- Current builder requests, proposer preferences, light-client branches, and
  all enclosing block, state, and envelope types.
- Minimal Gloas `PTC_SIZE=16`, including attestations and the state PTC window.

The public codecs use these release-specific, vector-verified schemas. Gloas
remains a draft; later releases may change layouts and roots. One local compiler
quota adjustment is documented in [vendor/PATCHES.md](vendor/PATCHES.md). It
allows the 46-field progressive state to compile and changes no SSZ algorithm.

Gnosis inherits its preset constants from Lodestar-Z and uses the same current
specification schemas. The Ethereum release publishes mainnet and minimal vectors, so
gnosis is covered by local round-trip, boundary, and preset-specific tests.

## Official test vectors

The repository includes a small, unchanged selection of official vectors in
`tests/vectors`, with release, archive hashes, and case paths in its manifest.
These run with the normal test suite. The full SSZ static suites for the three
forks can be extracted from the official release:

```sh
curl -fL https://github.com/ethereum/consensus-specs/releases/download/v1.7.0-beta.4/minimal.tar.gz -o /tmp/minimal.tar.gz
curl -fL https://github.com/ethereum/consensus-specs/releases/download/v1.7.0-beta.4/mainnet.tar.gz -o /tmp/mainnet.tar.gz
python tools/extract_vectors.py /tmp/minimal.tar.gz fixtures
python tools/extract_vectors.py /tmp/mainnet.tar.gz fixtures
python -m pytest -m spec
```

Use `--cases-per-suite 2` when extracting for a smaller sample. Set
`SSZ_SPEC_TESTS=/path/to/tests` to use an existing extracted release. Each case
checks SSZ decoding, byte-identical re-encoding, the published root, JSON input,
and JSON output round trips. The default-value suite also exercises every
exported type in all nine fork/preset combinations.

## Build and architecture

```sh
python -m pip install build
python -m build
```

A source distribution includes vendored native source. Building it produces a
platform wheel with the three shared libraries. To compile Zig directly:

```sh
python -m ziglang build -Doptimize=ReleaseSafe -Dcpu=baseline
python -m ziglang fmt --check build.zig native
```

`-Dpreset=minimal` builds only that preset. `zig-out` is for direct Zig builds;
Python packaging installs its own artifacts into `ssz_z/_native`.

Python uses `ctypes` to call a small C ABI. SSZ encoding, validation, decoding,
and Merkleization run in Lodestar-Z. The fast path retains validated SSZ bytes
and uses schema-directed native JSON parsing/formatting with bulk hex conversion.
The dictionary API normalizes JSON values in Python; SSZ serialization of those
values crosses through JSON once. JSON-only dictionary conversions no longer
round-trip through SSZ. `hash_tree_root_from_ssz` and block projections hash
serialized bytes directly. Native calls release the GIL and use independent
per-call arenas; dynamically returned buffers are copied into Python and freed
before returning. [native/bindings.h](native/bindings.h) documents ABI version 2.
Rebuild the package when updating from an earlier native ABI.
