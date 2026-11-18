//! Block production/publishing envelopes from ethereum/beacon-APIs at
//! 01e99a6530b22941f619bde525cbf8bb61991d42, types/{electra,fulu}/block_contents.yaml
//! and types/electra/block.yaml. Fulu reuses Electra's block/body schema.
const ssz = @import("ssz");
const preset = @import("preset").preset;
const constants = @import("constants");

pub fn Types(comptime Consensus: type, comptime is_fulu: bool) type {
    const Upstream = if (is_fulu) @import("upstream").fulu else @import("upstream").electra;
    return struct {
        const Blob = ssz.ByteVectorType(constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_BLOB);
        const Blobs = ssz.FixedListType(Blob, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
        const KZGProofs = ssz.FixedListType(
            ssz.ByteVectorType(48),
            preset.MAX_BLOB_COMMITMENTS_PER_BLOCK * if (is_fulu) preset.FIELD_ELEMENTS_PER_EXT_BLOB else 1,
            .{},
        );
        pub const BeaconBlockContents = ssz.VariableContainerType(struct {
            block: Consensus.BeaconBlock,
            kzg_proofs: KZGProofs,
            blobs: Blobs,
        });
        pub const SignedBeaconBlockContents = ssz.VariableContainerType(struct {
            signed_block: Consensus.SignedBeaconBlock,
            kzg_proofs: KZGProofs,
            blobs: Blobs,
        });
        pub const BlindedBeaconBlockBody = Upstream.BlindedBeaconBlockBody;
        pub const BlindedBeaconBlock = Upstream.BlindedBeaconBlock;
        pub const SignedBlindedBeaconBlock = Upstream.SignedBlindedBeaconBlock;
    };
}

pub fn GloasTypes(comptime Consensus: type) type {
    const Blob = ssz.ByteVectorType(constants.BYTES_PER_FIELD_ELEMENT * preset.FIELD_ELEMENTS_PER_BLOB);
    const Blobs = ssz.FixedListType(Blob, preset.MAX_BLOB_COMMITMENTS_PER_BLOCK, .{});
    const KZGProofs = ssz.FixedListType(
        ssz.ByteVectorType(48),
        preset.MAX_BLOB_COMMITMENTS_PER_BLOCK * preset.FIELD_ELEMENTS_PER_EXT_BLOB,
        .{},
    );
    return struct {
        pub const BeaconBlockContents = ssz.VariableContainerType(struct {
            block: Consensus.BeaconBlock,
            execution_payload_envelope: Consensus.ExecutionPayloadEnvelope,
            kzg_proofs: KZGProofs,
            blobs: Blobs,
        });
        pub const SignedExecutionPayloadEnvelopeContents = ssz.VariableContainerType(struct {
            signed_execution_payload_envelope: Consensus.SignedExecutionPayloadEnvelope,
            kzg_proofs: KZGProofs,
            blobs: Blobs,
        });
    };
}
