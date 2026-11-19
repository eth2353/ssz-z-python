const std = @import("std");
const ssz = @import("ssz");
const consensus = @import("consensus.zig");
const json_codec = @import("json.zig");
// hashtree lazily writes a non-atomic backend pointer on its first hash.
// Publish a completed warm-up before allowing concurrent native hashes.
var hash_initialization: std.atomic.Value(u8) = .init(0);

fn ensureHashInitialized() void {
    if (hash_initialization.load(.acquire) == 2) return;
    if (hash_initialization.cmpxchgStrong(0, 1, .acq_rel, .acquire) == null) {
        var root: [32]u8 = undefined;
        ssz.ByteVectorType(64).serialized.hashTreeRoot(&([_]u8{0} ** 64), &root) catch unreachable;
        hash_initialization.store(2, .release);
    } else {
        while (hash_initialization.load(.acquire) != 2) std.atomic.spinLoopHint();
    }
}

const max_input_size = 512 * 1024 * 1024;

// ABI values, mirrored by Python's _native.Operation and bindings.h.
const Operation = enum(u8) {
    json_to_ssz = 0,
    ssz_to_json = 1,
    hash_tree_root = 2,
    default_json = 3,
    type_schema = 4,
    list_types = 5,
    validate_ssz = 6,
    rest_json_to_ssz = 7,
    block_projection = 8,
    rest_metadata = 9,
    // Keep unknown bytes representable so they return an ABI error, not a trap.
    _,
};

// Each call owns an arena. Only the returned buffer crosses the ABI boundary;
// the caller releases it exactly once with ssz_z_free, including on errors.
export fn ssz_z_call(
    fork_ptr: [*]const u8,
    fork_len: usize,
    name_ptr: [*]const u8,
    name_len: usize,
    operation: u8,
    input_ptr: [*]const u8,
    input_len: usize,
    output_ptr: *?[*]u8,
    output_len: *usize,
) u8 {
    @setEvalBranchQuota(1_000_000);
    output_ptr.* = null;
    output_len.* = 0;
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    var writer: std.Io.Writer.Allocating = .init(std.heap.page_allocator);
    defer writer.deinit();
    dispatch(arena.allocator(), fork_ptr[0..fork_len], name_ptr[0..name_len], @enumFromInt(operation), input_ptr[0..input_len], &writer) catch |err| {
        const message = @errorName(err);
        const output = std.heap.page_allocator.dupe(u8, message) catch return 2;
        output_ptr.* = output.ptr;
        output_len.* = output.len;
        return 1;
    };
    if (writer.written().len == 0) return 0;
    const output = writer.toOwnedSlice() catch return 2;
    output_ptr.* = output.ptr;
    output_len.* = output.len;
    return 0;
}

export fn ssz_z_free(ptr: [*]u8, len: usize) void {
    std.heap.page_allocator.free(ptr[0..len]);
}

export fn ssz_z_abi_version() u32 {
    return 1;
}

fn dispatch(allocator: std.mem.Allocator, fork: []const u8, name: []const u8, operation: Operation, input: []const u8, writer: *std.Io.Writer.Allocating) !void {
    @setEvalBranchQuota(1_000_000);
    if (input.len > max_input_size) return error.InputTooLarge;
    inline for (.{ "primitive", "electra", "fulu", "gloas" }) |fork_name| {
        if (std.mem.eql(u8, fork, fork_name)) {
            const namespace = @field(consensus, fork_name);
            if (operation == .list_types) {
                var json: std.json.Stringify = .{ .writer = &writer.writer };
                try json.beginArray();
                inline for (@typeInfo(namespace).@"struct".decls) |decl| {
                    const T = @field(namespace, decl.name);
                    if (comptime @TypeOf(T) == type) {
                        if (@hasDecl(T, "kind")) try json.write(decl.name);
                    }
                }
                try json.endArray();
                return;
            }
            inline for (@typeInfo(namespace).@"struct".decls) |decl| {
                const T = @field(namespace, decl.name);
                if (comptime @TypeOf(T) == type) {
                    if (@hasDecl(T, "kind")) {
                        if (std.mem.eql(u8, name, decl.name)) return process(T, allocator, operation, input, writer);
                    }
                }
            }
            return error.UnknownType;
        }
    }
    return error.UnknownFork;
}

fn process(comptime T: type, allocator: std.mem.Allocator, operation: Operation, input: []const u8, writer: *std.Io.Writer.Allocating) !void {
    switch (operation) {
        .rest_metadata => return json_codec.restMetadata(allocator, input, writer),
        .type_schema => {
            var json: std.json.Stringify = .{ .writer = &writer.writer };
            return schema(T, &json);
        },
        .validate_ssz => return T.serialized.validate(input),
        .block_projection => {
            ensureHashInitialized();
            try T.serialized.validate(input);
            return @import("block_projection.zig").header(T, allocator, input, writer);
        },
        .hash_tree_root => {
            ensureHashInitialized();
            try T.serialized.validate(input);
            var root: [32]u8 = undefined;
            if (comptime ssz.isFixedType(T)) {
                try T.serialized.hashTreeRoot(input, &root);
            } else {
                try T.serialized.hashTreeRoot(allocator, input, &root);
            }
            return writer.writer.writeAll(&root);
        },
        .json_to_ssz, .ssz_to_json, .default_json, .rest_json_to_ssz => {},
        else => return error.UnknownOperation,
    }
    // BeaconState contains multi-megabyte fixed vectors; allocate it on the heap
    // so calls from Python worker threads do not exhaust their stacks.
    const value = try allocator.create(T.Type);
    value.* = T.default_value;
    if (operation == .json_to_ssz or operation == .rest_json_to_ssz) {
        var scanner = std.json.Scanner.initCompleteInput(allocator, input);
        defer scanner.deinit();
        if (operation == .rest_json_to_ssz) {
            try json_codec.readRest(T, allocator, &scanner, value);
        } else {
            try json_codec.read(T, allocator, &scanner, value);
        }
        if (try scanner.next() != .end_of_document) return error.TrailingJson;
        const size = if (comptime ssz.isFixedType(T)) T.fixed_size else T.serializedSize(value);
        if (size > max_input_size) return error.InputTooLarge;
        try writer.ensureUnusedCapacity(size);
        const bytes = try writer.writer.writableSlice(size);
        const written = T.serializeIntoBytes(value, bytes);
        if (written != size) return error.InvalidSize;
        try T.serialized.validate(bytes);
        return;
    }
    if (operation == .ssz_to_json) {
        try T.serialized.validate(input);
        if (comptime ssz.isFixedType(T)) {
            try T.deserializeFromBytes(input, value);
        } else {
            try T.deserializeFromBytes(allocator, input, value);
        }
    }
    try json_codec.write(T, allocator, writer, value);
}

fn schema(comptime T: type, json: *std.json.Stringify) !void {
    try json.beginObject();
    try json.objectField("kind");
    switch (T.kind) {
        .uint => {
            try json.write("uint");
            try json.objectField("bits");
            try json.write(T.fixed_size * 8);
        },
        .bool => try json.write("bool"),
        .container, .progressive_container => {
            try json.write("container");
            if (T.kind == .progressive_container) {
                try json.objectField("progressive");
                try json.write(true);
            }
            try json.objectField("fields");
            try json.beginObject();
            inline for (T.fields) |field| {
                try json.objectField(field.name);
                try schema(field.type, json);
            }
            try json.endObject();
        },
        .vector, .list => {
            const is_vector = T.kind == .vector;
            const is_bytes = if (is_vector) ssz.isByteVectorType(T) else ssz.isByteListType(T);
            const is_bits = if (is_vector) ssz.isBitVectorType(T) else ssz.isBitListType(T);
            try json.write(if (is_bytes) (if (is_vector) "bytevector" else "bytelist") else if (is_bits) (if (is_vector) "bitvector" else "bitlist") else if (is_vector) "vector" else "list");
            try json.objectField(if (is_vector) "length" else "limit");
            try json.write(if (is_vector) T.length else T.limit);
            if (!is_bytes and !is_bits) {
                try json.objectField("element");
                try schema(T.Element, json);
            }
        },
        .progressive_list, .progressive_bit_list => {
            const is_bytes = json_codec.isBytes(T);
            try json.write(if (T.kind == .progressive_bit_list) "bitlist" else if (is_bytes) "bytelist" else "list");
            try json.objectField("progressive");
            try json.write(true);
            if (T.kind == .progressive_list and !is_bytes) {
                try json.objectField("element");
                try schema(T.Element, json);
            }
        },
        else => @compileError("unsupported consensus SSZ kind"),
    }
    try json.endObject();
}
