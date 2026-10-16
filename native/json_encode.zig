//! Schema-controlled JSON: field names are static ASCII, and all dynamic strings
//! are decimal integers or hex. Write those directly into the growing buffer.
const std = @import("std");
const ssz = @import("ssz");

pub fn write(comptime T: type, allocator: std.mem.Allocator, out: *std.Io.Writer.Allocating, value: *const T.Type) anyerror!void {
    switch (T.kind) {
        .uint => try out.writer.print("\"{d}\"", .{value.*}),
        .bool => try out.writer.writeAll(if (value.*) "true" else "false"),
        .container, .progressive_container => {
            try out.writer.writeByte('{');
            inline for (T.fields, 0..) |field, i| {
                if (i > 0) try out.writer.writeByte(',');
                try out.writer.writeAll("\"" ++ field.name ++ "\":");
                try write(field.type, allocator, out, &@field(value, field.name));
            }
            try out.writer.writeByte('}');
        },
        .list, .vector, .progressive_list, .progressive_bit_list => {
            const is_bytes = comptime switch (T.kind) {
                .vector => ssz.isByteVectorType(T),
                .list => ssz.isByteListType(T),
                .progressive_list => @hasDecl(T, "is_bytes"),
                else => false,
            };
            const is_bits = comptime switch (T.kind) {
                .vector => ssz.isBitVectorType(T),
                .list => ssz.isBitListType(T),
                .progressive_bit_list => true,
                else => false,
            };
            if (comptime is_bytes) {
                return @import("hex.zig").write(if (T.kind == .vector) value[0..] else value.items, out);
            }
            if (comptime is_bits) {
                const size = if (comptime ssz.isFixedType(T)) T.fixed_size else T.serializedSize(value);
                const bytes = try allocator.alloc(u8, size);
                _ = T.serializeIntoBytes(value, bytes);
                return @import("hex.zig").write(bytes, out);
            }
            try out.writer.writeByte('[');
            const elements = if (T.kind == .vector) value[0..] else value.items;
            for (elements, 0..) |*element, i| {
                if (i > 0) try out.writer.writeByte(',');
                try write(T.Element, allocator, out, element);
            }
            try out.writer.writeByte(']');
        },
        else => @compileError("unsupported JSON type"),
    }
}
