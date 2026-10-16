//! Bulk hex conversion with one validation branch per byte pair and no formatting.
const std = @import("std");
const table: [256]u8 = blk: {
    var values: [256]u8 = @splat(255);
    for (0..10) |i| values['0' + i] = @intCast(i);
    for (0..6) |i| {
        values['a' + i] = @intCast(i + 10);
        values['A' + i] = @intCast(i + 10);
    }
    break :blk values;
};

pub fn decode(out: []u8, text: []const u8) !void {
    if (out.len * 2 != text.len) return error.InvalidHex;
    for (out, 0..) |*byte, i| {
        const high = table[text[2 * i]];
        const low = table[text[2 * i + 1]];
        if ((high | low) > 15) return error.InvalidHex;
        byte.* = (high << 4) | low;
    }
}

pub fn write(bytes: []const u8, writer: *std.Io.Writer.Allocating) !void {
    const len = bytes.len * 2 + 4;
    try writer.ensureUnusedCapacity(len);
    const out = try writer.writer.writableSlice(len);
    @memcpy(out[0..3], "\"0x");
    const alphabet = "0123456789abcdef";
    for (bytes, 0..) |byte, i| {
        out[3 + 2 * i] = alphabet[byte >> 4];
        out[4 + 2 * i] = alphabet[byte & 15];
    }
    out[len - 1] = '"';
}
