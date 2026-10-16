# Validation

Verified locally on macOS arm64 against these pinned sources:

- Lodestar-Z `main`: `ba4f89e967bdb498f1d856f699f1ba2b863be330`.
- Consensus specification: `v1.7.0-beta.4`, commit
  `aa16bb4c156184e9548a997d53efaf2a228a6304`.
- Zig 0.16.0, ReleaseSafe, baseline CPU.

## Official SSZ static vectors

All cases for Electra, Fulu, and Gloas were extracted from the official release
archives and passed under Python 3.14.6:

| Preset | Distinct cases |
| --- | ---: |
| minimal | 23,124 |
| mainnet | 940 |
| Total | 24,064 |

Each case verified decoding, byte-identical encoding, the published hash tree
root, JSON input conversion, and JSON output round trips. The run also included
75 bundled official smoke vectors and 105 binding tests: **24,244 passed**.
Every external case also exercised the SSZ-backed value loaders for both JSON
and SSZ, checking exact encoded bytes and roots.

Archive SHA-256 hashes:

- minimal.tar.gz: `26d09aea70c62ed235a120a95082d544ab1c2e6fe36bd35ea1bd5da62f3b7b68`
- mainnet.tar.gz: `67762986572372a08d3b182535aa760433c86e174e14e0bbd756f350dd19398c`

## Binding checks

The suite without external vector files passed **180 tests**, including the
75 bundled vectors and 105 local tests. It covers every exported codec's default
round trip across all nine fork/preset combinations; integer boundaries,
malformed JSON, offsets, lengths, bitfields, deterministic SSZ mutations,
concurrent calls, preset-specific sizes, and Gloas progressive hashing. Beacon
API coverage includes all five production/publishing codecs for Electra/Fulu
in all presets, Fulu cell-proof bounds, independent contents roots and SSZ
offsets, and matching full/blinded payload, body, block, and signed-block roots.

The SSZ-backed API additionally covers arbitrary JSON field order and escapes,
REST response envelopes, malformed/duplicate fields, immutable snapshots of
mutable inputs, scalar/header projection, signed wrappers with blob/proof data,
close/output lifetimes, concurrent reads and close, and native-call counts in
the proposal flow.

Gnosis has no vectors in the official Ethereum release. Its codecs passed the
local checks, using Lodestar-Z's gnosis constants and the same beta.4 schemas.

## Packaging

- Editable installation succeeded.
- Built a source distribution and then built a wheel from that distribution.
- Source distribution contains native source and no prebuilt native binaries.
- Wheel contains all three preset libraries and has no runtime dependencies.
- Clean Python 3.10.20 installation of the wheel passed round-trip and root
  checks for all 1,413 exported fork/preset codecs, including all three
  SSZ-backed loaders, JSON output, and context-manager lifetimes (version 0.2.0).
- Wheel tag: `py3-none-macosx_11_0_arm64`; native deployment target is macOS 11.0.
- Schema regeneration reproduces the committed generated source exactly.
- Ruff lint/format and Zig formatting checks passed.

Native ABI version is 2; Python and the three native libraries must be upgraded
together. See [the sampled performance report](performance/report.md) for the
separate, limited timing comparison. No full benchmark was run for this change.

Linux and Windows CI jobs are configured but were not executed on this host.
