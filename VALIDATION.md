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
75 bundled official smoke vectors: **24,139 passed**.

Archive SHA-256 hashes:

- minimal.tar.gz: `26d09aea70c62ed235a120a95082d544ab1c2e6fe36bd35ea1bd5da62f3b7b68`
- mainnet.tar.gz: `67762986572372a08d3b182535aa760433c86e174e14e0bbd756f350dd19398c`

## Binding checks

The suite without external vector files passed **121 tests**, including the
75 bundled vectors and 46 local tests. It covers every exported codec's default
round trip across all nine fork/preset combinations; integer boundaries,
malformed JSON, offsets, lengths, bitfields, deterministic SSZ mutations,
concurrent calls, preset-specific sizes, and Gloas progressive hashing.

Gnosis has no vectors in the official Ethereum release. Its codecs passed the
local checks, using Lodestar-Z's gnosis constants and the same beta.4 schemas.

## Packaging

- Editable installation succeeded.
- Built a source distribution and then built a wheel from that distribution.
- Source distribution contains native source and no prebuilt native binaries.
- Wheel contains all three preset libraries and has no runtime dependencies.
- Clean Python 3.10.20 installation of the wheel passed round-trip and root
  checks for all 1,401 exported fork/preset codecs.
- Wheel tag: `py3-none-macosx_11_0_arm64`; native deployment target is macOS 11.0.
- Schema regeneration reproduces the committed generated source exactly.
- Ruff lint/format and Zig formatting checks passed.

Linux and Windows CI jobs are configured but were not executed on this host.
