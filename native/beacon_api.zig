//! Block production/publishing envelopes from ethereum/beacon-APIs at
//! 01e99a6530b22941f619bde525cbf8bb61991d42, types/{electra,fulu}/block_contents.yaml
//! and types/electra/block.yaml. Fulu reuses Electra's block/body schema.
const std = @import("std");
const ssz = @import("ssz");
const preset = @import("preset").preset;
const constants = @import("constants");

pub fn Types(comptime Consensus: type, comptime is_fulu: bool) type {
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
        pub const BlindedBeaconBlockBody = blindedBody(Consensus);
        pub const BlindedBeaconBlock = ssz.VariableContainerType(struct {
            slot: Consensus.Slot,
            proposer_index: Consensus.ValidatorIndex,
            parent_root: Consensus.Root,
            state_root: Consensus.Root,
            body: BlindedBeaconBlockBody,
        });
        pub const SignedBlindedBeaconBlock = ssz.VariableContainerType(struct {
            message: BlindedBeaconBlock,
            signature: Consensus.BLSSignature,
        });
    };
}

fn blindedBody(comptime Consensus: type) type {
    const fields = Consensus.BeaconBlockBody.fields;
    comptime var names: [fields.len][:0]const u8 = undefined;
    comptime var types: [fields.len]type = undefined;
    comptime var attrs: [fields.len]std.builtin.Type.StructField.Attributes = undefined;
    inline for (fields, 0..) |field, i| {
        if (std.mem.eql(u8, field.name, "execution_payload")) {
            names[i] = "execution_payload_header";
            types[i] = Consensus.ExecutionPayloadHeader;
        } else {
            names[i] = field.name;
            types[i] = field.type;
        }
        attrs[i] = .{};
    }
    return ssz.VariableContainerType(@Struct(.auto, null, &names, &types, &attrs));
}
