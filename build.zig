const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    if (target.result.os.tag != .linux or (target.result.cpu.arch != .x86_64 and target.result.cpu.arch != .aarch64)) {
        @panic("ssz-z-python supports Linux AMD64 and ARM64 only");
    }
    const optimize = b.standardOptimizeOption(.{});
    const selected = b.option([]const u8, "preset", "Build one preset instead of all three");
    const python = b.option([]const u8, "python", "Python interpreter used to fetch native sources") orelse "python3";
    const fetch = b.addSystemCommand(&.{ python, b.pathFromRoot("tools/fetch_native.py") });
    const sources = std.json.parseFromSlice(std.json.Value, b.allocator, @embedFile("UPSTREAM.json"), .{}) catch @panic("invalid UPSTREAM.json");
    const lodestar = dependencyPath(b, sources.value, "lodestar");
    const hashtree_z = dependencyPath(b, sources.value, "hashtree-z");
    const hashtree_c = dependencyPath(b, sources.value, "hashtree");
    const hash = b.addLibrary(.{
        .name = "hashtree",
        .linkage = .static,
        .root_module = b.createModule(.{ .target = target, .optimize = optimize, .link_libc = true, .pic = true }),
    });
    hash.step.dependOn(&fetch.step);
    const arch = target.result.cpu.arch;
    if (arch == .aarch64) {
        hash.root_module.addCSourceFiles(.{
            .root = hashtree_c.path(b, "src"),
            .files = &.{ "sha256_armv8_neon_x4.S", "sha256_armv8_neon_x1.S", "sha256_armv8_crypto.S" },
            .flags = &.{ "-g", "-fpic" },
        });
    } else {
        hash.root_module.addCSourceFiles(.{
            .root = hashtree_c.path(b, "src"),
            .files = &.{ "sha256_shani.S", "sha256_avx_x16.S", "sha256_avx_x8.S", "sha256_avx_x4.S", "sha256_avx_x1.S", "sha256_sse_x1.S" },
            .flags = &.{ "-g", "-fpic", "-fno-integrated-as" },
        });
    }
    hash.root_module.addCSourceFiles(.{
        .root = hashtree_c.path(b, "src"),
        .files = &.{ "hashtree.c", "sha256_generic.c" },
        .flags = &.{ "-g", "-Wall", "-Werror" },
    });
    hash.root_module.addIncludePath(hashtree_c.path(b, "src"));
    const hashtree = b.createModule(.{ .root_source_file = hashtree_z.path(b, "src/root.zig"), .target = target, .optimize = optimize });
    hashtree.addIncludePath(hashtree_c.path(b, "src"));
    hashtree.linkLibrary(hash);

    var matched = false;
    for (sources.value.object.get("bindings").?.object.get("presets").?.array.items) |preset_entry| {
        const preset_name = preset_entry.string;
        if (selected) |name| {
            if (!std.mem.eql(u8, name, preset_name)) continue;
        }
        matched = true;
        const options = b.addOptions();
        options.addOption(u32, "abi_version", @intCast(sources.value.object.get("bindings").?.object.get("abi_version").?.integer));
        options.addOption([]const u8, "preset", preset_name);
        options.addOption(?u8, "zero_hash_max_depth", null);
        options.addOption(?bool, "expensive_safety_checks", null);
        const build_options = options.createModule();
        const constants = module(b, lodestar, target, optimize, "src/constants/root.zig");
        const hex = module(b, lodestar, target, optimize, "src/hex.zig");
        const bits = module(b, lodestar, target, optimize, "src/bit_array/root.zig");
        const allocators = module(b, lodestar, target, optimize, "src/testing_allocators.zig");
        const hashing = module(b, lodestar, target, optimize, "src/hashing/root.zig");
        hashing.addImport("build_options", build_options);
        hashing.addImport("hex", hex);
        hashing.addImport("hashtree", hashtree);
        const pmt = module(b, lodestar, target, optimize, "src/persistent_merkle_tree/root.zig");
        pmt.addImport("build_options", build_options);
        pmt.addImport("hex", hex);
        pmt.addImport("hashing", hashing);
        const ssz = module(b, lodestar, target, optimize, "src/ssz/root.zig");
        ssz.addImport("build_options", build_options);
        ssz.addImport("bit_array", bits);
        ssz.addImport("hex", hex);
        ssz.addImport("hashing", hashing);
        ssz.addImport("persistent_merkle_tree", pmt);
        ssz.addImport("testing_allocators", allocators);
        const preset = module(b, lodestar, target, optimize, "src/preset/root.zig");
        preset.addImport("build_options", build_options);
        preset.addImport("constants", constants);
        const upstream = module(b, lodestar, target, optimize, "src/consensus_types/root.zig");
        upstream.addImport("ssz", ssz);
        upstream.addImport("preset", preset);
        upstream.addImport("constants", constants);
        upstream.addImport("build_options", build_options);
        const root = b.createModule(.{ .root_source_file = b.path("native/bindings.zig"), .target = target, .optimize = optimize, .link_libc = true });
        root.addImport("build_options", build_options);
        root.addImport("ssz", ssz);
        root.addImport("preset", preset);
        root.addImport("constants", constants);
        root.addImport("upstream", upstream);
        const lib = b.addLibrary(.{ .name = b.fmt("ssz_z_{s}", .{preset_name}), .linkage = .dynamic, .root_module = root });
        lib.step.dependOn(&fetch.step);
        b.installArtifact(lib);
    }
    if (selected != null and !matched) @panic("unknown preset");
}

fn module(b: *std.Build, source: std.Build.LazyPath, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode, path: []const u8) *std.Build.Module {
    return b.createModule(.{ .root_source_file = source.path(b, path), .target = target, .optimize = optimize });
}

fn dependencyPath(b: *std.Build, manifest: std.json.Value, name: []const u8) std.Build.LazyPath {
    const commit = manifest.object.get(name).?.object.get("commit").?.string;
    return b.path(b.fmt("build/deps/{s}/{s}", .{ name, commit }));
}
