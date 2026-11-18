# Validation

Verified locally on macOS arm64 against these pinned sources:

- Lodestar `unstable`: `0ac7778d7034693a0818296dbe717f2999576ab1`.
- Consensus specification: `v1.7.0-beta.4`, commit
  `aa16bb4c156184e9548a997d53efaf2a228a6304`.
- Zig 0.16.0, ReleaseSafe, baseline CPU.

The November 18, 2026 refresh follows development from the archived Lodestar-Z
repository into the active Lodestar monorepo. Native sources are fetched from
commit-pinned archives, checked against SHA-256 hashes in `UPSTREAM.json`, and
cached under `build/deps`. Downloaded sources were compared byte-for-byte with
the previously validated snapshots before removing `vendor/`. Third-party
license notices remain in `licenses/`. There are no local native patches.
The bindings use upstream's progressive byte-list type, minimal
`PTC_SIZE=16`, and Gloas sync-committee/finality generalized indices directly.
The hashtree dependencies remain at the revisions pinned by upstream.

## Official SSZ static vectors

All cases for Electra, Fulu, and Gloas were extracted from the official release
archives and passed under both Python 3.12.16 and Python 3.15.2:

| Preset | Distinct cases |
| --- | ---: |
| minimal | 23,124 |
| mainnet | 940 |
| Total | 24,064 |

Each case verified decoding, byte-identical encoding, the published hash tree
root, JSON input conversion, and JSON output round trips. The run also included
75 bundled official smoke vectors, 108 binding tests, one schema-generator
regression test, and three dependency-fetch tests: **24,251 passed**.
Every external case also exercised the SSZ-backed value loaders for both JSON
and SSZ, checking exact encoded bytes and roots.

Archive SHA-256 hashes:

- minimal.tar.gz: `26d09aea70c62ed235a120a95082d544ab1c2e6fe36bd35ea1bd5da62f3b7b68`
- mainnet.tar.gz: `67762986572372a08d3b182535aa760433c86e174e14e0bbd756f350dd19398c`

## Binding checks

The suite without external vector files passed **187 tests**, including the
75 bundled vectors and 112 local tests. It covers every exported codec's default
round trip across all nine fork/preset combinations; integer boundaries,
malformed JSON, offsets, lengths, bitfields, deterministic SSZ mutations,
concurrent calls, preset-specific sizes, and Gloas progressive hashing. Beacon
API coverage includes all five production/publishing codecs for Electra/Fulu
in all presets, Fulu cell-proof bounds, independent contents roots and SSZ
offsets, and matching full/blinded payload, body, block, and signed-block roots.

The catalog rejects legacy type-name aliases and resolves fork types directly
from the generated release schemas.

The SSZ-backed API additionally covers arbitrary JSON field order and escapes,
REST response envelopes, malformed/duplicate fields, immutable snapshots of
mutable inputs, scalar/header projection, signed wrappers with blob/proof data,
frozen values and independent output lifetimes, concurrent reads/signing, and
native-call counts in the proposal flow. Progressive byte lists retain hex JSON
while progressive participation lists retain arrays of decimal strings.

Gnosis has no vectors in the official Ethereum release. Its codecs passed the
local checks, using Lodestar-Z's gnosis constants and the same beta.4 schemas.
Gnosis was already present in the previous upstream pin and remains available
in the active source. Schema generation now rejects an incomplete specification
checkout without overwriting the existing generated file.
Dependency-fetch tests cover offline cache reuse, checksum rejection, and
archive path traversal rejection.

## Packaging

- Editable installation succeeded.
- Built a source distribution and then built a wheel from that distribution.
- Source distribution contains bindings, dependency pins/checksums, and license
  notices, with no dependency source snapshots or prebuilt native binaries.
- Building the source distribution fetches and verifies uncached sources.
- Wheel contains all three preset libraries and has no runtime dependencies.
- Clean Python 3.12.16 and Python 3.15.2 installations of the wheel passed SSZ
  round-trip and root checks for all 1,368 canonical fork/preset codecs.
- Wheel metadata requires Python 3.12 or newer.
- Wheel tag: `py3-none-macosx_11_0_arm64`; native deployment target is macOS 11.0.
- Schema regeneration reproduces the committed generated source exactly.
- Ruff lint/format and Zig formatting checks passed.

Native ABI version is 1; Python and the three native libraries must be upgraded
together. See [the sampled performance report](performance/report.md) for the
separate, limited timing comparison. No full benchmark was run for this change.

CI tests and builds on Linux with Python 3.12 and Python 3.15. These local checks
ran on macOS arm64; the GitHub Actions workflow was not executed on this host.
