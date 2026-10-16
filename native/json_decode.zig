//! Order-independent, schema-directed JSON decoding into upstream value types.
//! An arena owns every allocation, including partially decoded values on errors.
const std = @import("std");
const ssz = @import("ssz");
const max_size = 512 * 1024 * 1024;

fn token(scanner: *std.json.Scanner, allocator: std.mem.Allocator) !std.json.Token {
    return scanner.nextAllocMax(allocator, .alloc_if_needed, max_size);
}

fn string(scanner: *std.json.Scanner, allocator: std.mem.Allocator) ![]const u8 {
    return switch (try token(scanner, allocator)) {
        .string, .allocated_string => |s| s,
        else => error.InvalidJson,
    };
}

pub fn read(comptime T: type, allocator: std.mem.Allocator, scanner: *std.json.Scanner, out: *T.Type) anyerror!void {
    @setEvalBranchQuota(1_000_000);
    switch (T.kind) {
        .container, .progressive_container => {
            if (try scanner.next() != .object_begin) return error.InvalidJson;
            var seen: [T.fields.len]bool = @splat(false);
            var count: usize = 0;
            while (try scanner.peekNextTokenType() != .object_end) {
                const key = try string(scanner, allocator);
                inline for (T.fields, 0..) |field, i| {
                    if (std.mem.eql(u8, field.name, key)) {
                        if (seen[i]) return error.DuplicateField;
                        seen[i] = true;
                        count += 1;
                        try read(field.type, allocator, scanner, &@field(out, field.name));
                        break;
                    }
                } else return error.UnknownField;
            }
            _ = try scanner.next();
            if (count != T.fields.len) return error.MissingField;
        },
        .uint => {
            const number = switch (try token(scanner, allocator)) {
                .string, .allocated_string, .number, .allocated_number => |s| s,
                else => return error.InvalidJson,
            };
            if (number.len == 0) return error.InvalidInteger;
            for (number) |digit| {
                if (digit < '0' or digit > '9') return error.InvalidInteger;
            }
            out.* = try std.fmt.parseInt(T.Type, number, 10);
        },
        .bool => {
            out.* = switch (try scanner.next()) {
                .true => true,
                .false => false,
                else => return error.InvalidJson,
            };
        },
        .vector, .list, .progressive_list, .progressive_bit_list => {
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
            if (comptime is_bytes or is_bits) {
                const text = try string(scanner, allocator);
                if (text.len < 2 or !std.mem.startsWith(u8, text, "0x") or text.len % 2 != 0) return error.InvalidHex;
                const len = (text.len - 2) / 2;
                if (comptime is_bytes) {
                    if (T.kind == .vector) {
                        if (len != T.length) return error.InvalidSize;
                        try @import("hex.zig").decode(out[0..], text[2..]);
                    } else {
                        if (T.kind == .list and len > T.limit) return error.gtLimit;
                        try out.resize(allocator, len);
                        try @import("hex.zig").decode(out.items, text[2..]);
                    }
                } else {
                    const bytes = try allocator.alloc(u8, len);
                    try @import("hex.zig").decode(bytes, text[2..]);
                    if (comptime ssz.isFixedType(T)) {
                        try T.deserializeFromBytes(bytes, out);
                    } else {
                        try T.deserializeFromBytes(allocator, bytes, out);
                    }
                }
                return;
            }
            if (try scanner.next() != .array_begin) return error.InvalidJson;
            var index: usize = 0;
            while (try scanner.peekNextTokenType() != .array_end) : (index += 1) {
                if (comptime T.kind == .vector) {
                    if (index >= T.length) return error.InvalidSize;
                    try read(T.Element, allocator, scanner, &out[index]);
                } else {
                    if (comptime T.kind == .list) {
                        if (index >= T.limit) return error.gtLimit;
                    }
                    const element = try out.addOne(allocator);
                    element.* = T.Element.default_value;
                    try read(T.Element, allocator, scanner, element);
                }
            }
            _ = try scanner.next();
            if (comptime T.kind == .vector) {
                if (index != T.length) return error.InvalidSize;
            }
        },
        else => @compileError("unsupported JSON type"),
    }
}

pub fn readRest(comptime T: type, allocator: std.mem.Allocator, scanner: *std.json.Scanner, out: *T.Type) !void {
    if (try scanner.next() != .object_begin) return error.InvalidJson;
    var keys: std.StringHashMap(void) = .init(allocator);
    var found = false;
    while (try scanner.peekNextTokenType() != .object_end) {
        const key = try string(scanner, allocator);
        const entry = try keys.getOrPut(key);
        if (entry.found_existing) return error.DuplicateField;
        if (std.mem.eql(u8, key, "data")) {
            try read(T, allocator, scanner, out);
            found = true;
        } else {
            try scanner.skipValue();
        }
    }
    _ = try scanner.next();
    if (!found) return error.MissingData;
}
