//! Project block headers from validated serialized data, without materializing
//! transactions, attestations, proofs, or blobs. Only the body needs hashing.
const std = @import("std");
const ssz = @import("ssz");
const consensus = @import("consensus.zig");

pub fn header(comptime T: type, allocator: std.mem.Allocator, data: []const u8, writer: *std.Io.Writer.Allocating) anyerror!void {
    if (comptime T.kind != .container and T.kind != .progressive_container) return error.NotABlock;
    if (comptime @hasField(T.Type, "block")) return descend(T, "block", allocator, data, writer);
    if (comptime @hasField(T.Type, "signed_block")) return descend(T, "signed_block", allocator, data, writer);
    if (comptime @hasField(T.Type, "message")) return descend(T, "message", allocator, data, writer);
    if (comptime !@hasField(T.Type, "body") or !@hasField(T.Type, "slot") or !@hasField(T.Type, "proposer_index")) return error.NotABlock;
    const Body = T.getFieldType("body");
    const ranges = try T.readFieldRanges(data);
    var bytes: [112]u8 = undefined;
    comptime var offset: usize = 0;
    inline for (.{ "slot", "proposer_index", "parent_root", "state_root" }) |field| {
        const len = T.getFieldType(field).fixed_size;
        const range = ranges[comptime T.getFieldIndex(field)];
        @memcpy(bytes[offset..][0..len], data[range[0]..range[1]]);
        offset += len;
    }
    const body = ranges[comptime T.getFieldIndex("body")];
    if (comptime ssz.isFixedType(Body)) {
        try Body.serialized.hashTreeRoot(data[body[0]..body[1]], bytes[80..112]);
    } else {
        try Body.serialized.hashTreeRoot(allocator, data[body[0]..body[1]], bytes[80..112]);
    }
    var root: [32]u8 = undefined;
    try consensus.electra.BeaconBlockHeader.serialized.hashTreeRoot(&bytes, &root);
    try writer.writer.writeAll(&bytes);
    try writer.writer.writeAll(&root);
}

fn descend(comptime T: type, comptime field: []const u8, allocator: std.mem.Allocator, data: []const u8, writer: *std.Io.Writer.Allocating) !void {
    const index = comptime T.getFieldIndex(field);
    if (comptime ssz.isFixedType(T)) {
        const start = T.field_offsets[index];
        return header(T.getFieldType(field), allocator, data[start..][0..T.getFieldType(field).fixed_size], writer);
    }
    const ranges = try T.readFieldRanges(data);
    const range = ranges[index];
    return header(T.getFieldType(field), allocator, data[range[0]..range[1]], writer);
}
