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

Python uses `ctypes` to call a small C ABI. Conversion between Python objects and
native values passes through consensus JSON; SSZ encoding, validation, decoding,
and Merkleization run in Lodestar-Z. `hash_tree_root_from_ssz` hashes serialized
bytes directly, avoiding Python object/JSON conversion. Native calls release
the GIL, use independent per-call arenas, and copy returned data into Python
before freeing it. [native/bindings.h](native/bindings.h) documents the ABI.
