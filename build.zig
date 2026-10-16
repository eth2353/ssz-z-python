const std = @import("std");
const builtin = @import("builtin");

pub fn build(b: *std.Build) void {
    var target_query = b.standardTargetOptionsQueryOnly(.{});
    if (builtin.os.tag == .macos and target_query.os_tag == null) {
        target_query.os_version_min = .{ .semver = .{ .major = 11, .minor = 0, .patch = 0 } };
    }
    const target = b.resolveTargetQuery(target_query);
    const optimize = b.standardOptimizeOption(.{});
    const selected = b.option([]const u8, "preset", "Build one preset instead of all three");
    const hash = b.addLibrary(.{
        .name = "hashtree",
        .linkage = .static,
        .root_module = b.createModule(.{ .target = target, .optimize = optimize, .link_libc = true, .pic = true }),
    });
    const arch = target.result.cpu.arch;
    const os = target.result.os.tag;
    if (arch.isArm() or arch.isAARCH64()) {
        hash.root_module.addCSourceFiles(.{
            .root = b.path("vendor/hashtree/src"),
            .files = &.{ "sha256_armv8_neon_x4.S", "sha256_armv8_neon_x1.S", "sha256_armv8_crypto.S" },
            .flags = &.{ "-g", "-fpic" },
        });
    } else if (arch.isX86() and os != .macos and !(os == .windows and target.result.abi == .msvc)) {
        hash.root_module.addCSourceFiles(.{
            .root = b.path("vendor/hashtree/src"),
            .files = &.{ "sha256_shani.S", "sha256_avx_x16.S", "sha256_avx_x8.S", "sha256_avx_x4.S", "sha256_avx_x1.S", "sha256_sse_x1.S" },
            .flags = &.{ "-g", "-fpic", "-fno-integrated-as" },
        });
    }
    hash.root_module.addCSourceFiles(.{
        .root = b.path("vendor/hashtree/src"),
        .files = &.{ "hashtree.c", "sha256_generic.c" },
        .flags = &.{ "-g", "-Wall", "-Werror" },
    });
    hash.root_module.addIncludePath(b.path("vendor/hashtree/src"));
    const hashtree = b.createModule(.{ .root_source_file = b.path("vendor/hashtree-z/src/root.zig"), .target = target, .optimize = optimize });
    hashtree.addIncludePath(b.path("vendor/hashtree/src"));
    hashtree.linkLibrary(hash);

    for ([_][]const u8{ "mainnet", "minimal", "gnosis" }) |preset_name| {
        if (selected) |name| {
            if (!std.mem.eql(u8, name, preset_name)) continue;
        }
        const options = b.addOptions();
        options.addOption([]const u8, "preset", preset_name);
        options.addOption(?u8, "zero_hash_max_depth", null);
        const build_options = options.createModule();
        const constants = module(b, target, optimize, "src/constants/root.zig");
        const hex = module(b, target, optimize, "src/hex.zig");
        const bits = module(b, target, optimize, "src/bit_array/root.zig");
        const allocators = module(b, target, optimize, "src/testing_allocators.zig");
        const hashing = module(b, target, optimize, "src/hashing/root.zig");
        hashing.addImport("build_options", build_options);
        hashing.addImport("hex", hex);
        hashing.addImport("hashtree", hashtree);
        const pmt = module(b, target, optimize, "src/persistent_merkle_tree/root.zig");
        pmt.addImport("build_options", build_options);
        pmt.addImport("hex", hex);
        pmt.addImport("hashing", hashing);
        const ssz = module(b, target, optimize, "src/ssz/root.zig");
        ssz.addImport("build_options", build_options);
        ssz.addImport("bit_array", bits);
        ssz.addImport("hex", hex);
        ssz.addImport("hashing", hashing);
        ssz.addImport("persistent_merkle_tree", pmt);
        ssz.addImport("testing_allocators", allocators);
        const preset = module(b, target, optimize, "src/preset/root.zig");
        preset.addImport("build_options", build_options);
        preset.addImport("constants", constants);
        const consensus = module(b, target, optimize, "src/consensus_types/root.zig");
        consensus.addImport("build_options", build_options);
        consensus.addImport("ssz", ssz);
        consensus.addImport("constants", constants);
        consensus.addImport("preset", preset);
        const root = b.createModule(.{ .root_source_file = b.path("native/bindings.zig"), .target = target, .optimize = optimize, .link_libc = true });
        root.addImport("ssz", ssz);
        root.addImport("preset", preset);
        root.addImport("constants", constants);
        root.addImport("consensus_types", consensus);
        const lib = b.addLibrary(.{ .name = b.fmt("ssz_z_{s}", .{preset_name}), .linkage = .dynamic, .root_module = root });
        b.installArtifact(lib);
    }
    if (selected) |name| {
        if (!std.mem.eql(u8, name, "mainnet") and !std.mem.eql(u8, name, "minimal") and !std.mem.eql(u8, name, "gnosis")) @panic("unknown preset");
    }
}

fn module(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode, path: []const u8) *std.Build.Module {
    return b.createModule(.{ .root_source_file = b.path(b.fmt("vendor/lodestar-z/{s}", .{path})), .target = target, .optimize = optimize });
}
