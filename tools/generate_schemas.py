"""Generate Lodestar-Z types from the v1.7.0-beta.4 specification's class declarations.

Only Python syntax is parsed; no specification code is executed. Regenerate with:
python tools/generate_schemas.py /path/to/consensus-specs native/consensus.zig
"""

import argparse
import ast
import re
from pathlib import Path

FORKS = ("phase0", "altair", "bellatrix", "capella", "deneb", "electra", "fulu", "gloas")
VERSION = "v1.7.0-beta.4"
COMMIT = "aa16bb4c156184e9548a997d53efaf2a228a6304"
ROOT = Path(__file__).resolve().parents[1]

# Spec-defined generalized index, which upstream does not yet expose.
GINDICES = {
    "EXECUTION_BLOCK_HASH_GINDEX_GLOAS": 2856,
}


class Generator:
    def __init__(self, definitions):
        self.definitions = definitions
        self.output = {}
        self.fixed = {}
        self.preset_names = set(
            re.findall(
                r"pub const (\w+)", (ROOT / "vendor/lodestar-z/src/preset/preset.zig").read_text()
            )
        )
        self.constants = set(
            re.findall(
                r"pub const (\w+)", (ROOT / "vendor/lodestar-z/src/constants/root.zig").read_text()
            )
        )
        self.preset_module_names = set(
            re.findall(
                r"pub const (\w+)", (ROOT / "vendor/lodestar-z/src/preset/root.zig").read_text()
            )
        )

    def bound(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return str(node.value)
        if isinstance(node, ast.Name):
            name = node.id
            if name in GINDICES:
                return str(GINDICES[name])
            if name in self.constants:
                return f"constants.{name}"
            if name in self.preset_names:
                return f"preset.{name}"
            if name in self.preset_module_names:
                return f"preset_module.{name}"
            raise ValueError(f"Unknown bound: {name}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if re.fullmatch(r"Uint\d+", name):
                return self.bound(node.args[0])
            if name == "floorlog2":
                return f"std.math.log2({self.bound(node.args[0])})"
        if isinstance(node, ast.BinOp):
            left, right = self.bound(node.left), self.bound(node.right)
            if isinstance(node.op, ast.FloorDiv):
                return f"@divFloor({left}, {right})"
            if isinstance(node.op, ast.Pow):
                return f"std.math.pow(usize, {left}, {right})"
            operator = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Mod: "%"}[type(node.op)]
            return f"({left} {operator} {right})"
        raise ValueError(f"Unsupported bound: {ast.unparse(node)}")

    def reference(self, node):
        if not isinstance(node, ast.Name):
            raise ValueError(f"Unsupported type: {ast.unparse(node)}")
        name = node.id
        if name in self.fixed:
            return name
        if name == "Boolean":
            code, fixed = "ssz.BoolType()", True
        elif name == "Byte":
            code, fixed = "ssz.UintType(8)", True
        elif match := re.fullmatch(r"Uint(8|16|32|64|128|256)", name):
            code, fixed = f"ssz.UintType({match[1]})", True
        elif match := re.fullmatch(r"Bytes(\d+)", name):
            code, fixed = f"ssz.ByteVectorType({match[1]})", True
        else:
            if name not in self.definitions:
                raise ValueError(f"Unknown type: {name}")
            cls = self.definitions[name]
            base = cls.bases[0]
            base_name = base.value.id if isinstance(base, ast.Subscript) else base.id
            attributes = {
                item.targets[0].id: item.value
                for item in cls.body
                if isinstance(item, ast.Assign) and isinstance(item.targets[0], ast.Name)
            }
            if base_name in {"Container", "ProgressiveContainer"}:
                fields = [
                    (item.target.id, self.reference(item.annotation))
                    for item in cls.body
                    if isinstance(item, ast.AnnAssign)
                ]
                fixed = all(self.fixed[child] for _, child in fields)
                progressive = base_name == "ProgressiveContainer"
                constructor = "Fixed" if fixed else "Variable"
                constructor += "ProgressiveContainerType" if progressive else "ContainerType"
                code = f"ssz.{constructor}(struct {{\n"
                code += "".join(f"    {key}: {child},\n" for key, child in fields)
                code += "}"
                if progressive:
                    width = attributes["ACTIVE_FIELDS"].keywords[0].value.value
                    if width != len(fields):
                        raise ValueError("Noncontiguous active fields need explicit support")
                    code += f", &([_]u1{{1}} ** {width})"
                code += ")"
            elif base_name in {
                "List",
                "Vector",
                "ProgressiveList",
                "BitList",
                "BitVector",
                "ByteList",
                "ByteVector",
                "ProgressiveBitList",
            }:
                fixed = base_name in {"Vector", "BitVector", "ByteVector"}
                if base_name == "ProgressiveBitList":
                    code = "ssz.ProgressiveBitListType(.{})"
                elif base_name in {"List", "Vector", "ProgressiveList"}:
                    child = self.reference(base.slice)
                    child_fixed = self.fixed[child]
                    if base_name == "ProgressiveList" and child == "Byte":
                        code = "ssz.ProgressiveByteListType(.{})"
                    else:
                        constructor = "Fixed" if child_fixed else "Variable"
                        constructor += {
                            "List": "ListType",
                            "Vector": "VectorType",
                            "ProgressiveList": "ProgressiveListType",
                        }[base_name]
                        code = f"ssz.{constructor}({child}"
                        if base_name != "ProgressiveList":
                            bound = self.bound(attributes["LENGTH" if fixed else "LIMIT"])
                            code += f", {bound}"
                            if child_fixed:
                                code += ", .{}"
                        else:
                            code += ", .{}"
                        code += ")"
                    if base_name == "Vector":
                        fixed = child_fixed
                else:
                    bound = self.bound(attributes["LENGTH" if fixed else "LIMIT"])
                    code = f"ssz.{base_name}Type({bound})"
            else:
                code = self.reference(base)
                fixed = self.fixed[code]
        self.output[name] = code
        self.fixed[name] = fixed
        return name


def generate(spec_root, destination):
    definitions = {}
    sections = []
    for fork in FORKS:
        paths = sorted(
            (spec_root / "specs" / fork).rglob("*.md"),
            key=lambda p: ("beacon-chain" not in str(p), str(p)),
        )
        if not paths:
            raise ValueError(f"No specification Markdown found for {fork}: {spec_root}")
        for path in paths:
            for block in re.findall(r"```python\n(.*?)```", path.read_text(), re.S):
                for node in ast.parse(block).body:
                    if isinstance(node, ast.ClassDef) and len(node.bases) == 1:
                        base = node.bases[0]
                        if isinstance(base, (ast.Name, ast.Subscript)):
                            definitions[node.name] = node
        if fork not in {"electra", "fulu", "gloas"}:
            continue
        generator = Generator(definitions)
        # Every container is a public codec; collection/scalar aliases are emitted
        # whenever one of those containers depends on them.
        for name, cls in definitions.items():
            if isinstance(cls.bases[0], ast.Name) and cls.bases[0].id in {
                "Container",
                "ProgressiveContainer",
            }:
                generator.reference(ast.Name(id=name))
        body = "\n".join(f"pub const {name} = {code};" for name, code in generator.output.items())
        if fork in {"electra", "fulu"}:
            is_fulu = str(fork == "fulu").lower()
            body += f'\nconst api = @import("beacon_api.zig").Types(@This(), {is_fulu});'
            for name in (
                "BeaconBlockContents",
                "SignedBeaconBlockContents",
                "BlindedBeaconBlockBody",
                "BlindedBeaconBlock",
                "SignedBlindedBeaconBlock",
            ):
                body += f"\npub const {name} = api.{name};"
        sections.append(f"pub const {fork} = struct {{\n{body}\n}};")
    header = f"""//! Generated from ethereum/consensus-specs {VERSION} ({COMMIT}).
//! Regenerate with tools/generate_schemas.py. The engine is Lodestar-Z SSZ.
const std = @import("std");
const ssz = @import("ssz");
const constants = @import("constants");
const preset_module = @import("preset");
const preset = preset_module.preset;
pub const primitive = @import("primitive");
"""
    destination.write_text(header + "\n".join(sections) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    generate(args.spec_root, args.destination)
