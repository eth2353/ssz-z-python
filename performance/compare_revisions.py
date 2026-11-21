# ruff: noqa: B023
# Loop callbacks execute synchronously before advancing to the next library.
"""Compare two ssz-z-python source trees in one process on paired block files."""

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import platform
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--before-source", type=Path, required=True)
parser.add_argument("--before-revision", required=True)
parser.add_argument("--before-dependencies", type=Path, required=True)
parser.add_argument("--corpus", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--rounds", type=int, default=3)
args = parser.parse_args()
if args.rounds < 1:
    parser.error("--rounds must be positive")
sys.path.append(str(args.before_dependencies.resolve()))

import ssz_z  # noqa: E402
from ssz_z.beacon_api import BlockValue  # noqa: E402

before_package = args.before_source.resolve() / "src/ssz_z"
spec = importlib.util.spec_from_file_location(
    "ssz_z_before",
    before_package / "__init__.py",
    submodule_search_locations=[str(before_package)],
)
before = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = before
spec.loader.exec_module(before)
before_api = __import__("ssz_z_before.beacon_api", fromlist=["BlockValue"])
libs = {"before": (before, before_api.BlockValue), "after": (ssz_z, BlockValue)}
args.output.mkdir(parents=True, exist_ok=True)

metadata = {
    "python": sys.version,
    "platform": platform.platform(),
    "before_revision": args.before_revision,
    "after_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),  # noqa: S607 - Trusted local command and arguments.
    "corpus": str(args.corpus.resolve()),
    "rounds": args.rounds,
    "method": "Same process; alternate library order by block/pass; 12 warmups; "
    "GC disabled; validation outside operation timers; median of pass means.",
    "native_build": {"zig": "0.16.0", "optimize": "ReleaseSafe", "cpu": "baseline"},
    "source_hashes": {},
    "inputs": [],
}
for label, (module, _) in libs.items():
    package = Path(module.__file__).parent
    metadata["source_hashes"][label] = {
        str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(package.rglob("*"))
        if p.is_file() and p.suffix in {".py", ".so", ".dylib", ".json"}
    }
metadata["harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
cases = []
json_paths = sorted((args.corpus / "json").glob("*.json"), key=lambda p: int(p.stem))
assert {p.stem for p in json_paths} == {p.stem for p in (args.corpus / "ssz").glob("*.ssz")}
for path in json_paths:
    js = path.read_bytes()
    ss = (args.corpus / "ssz" / (path.stem + ".ssz")).read_bytes()
    doc = json.loads(js)
    assert doc["version"] == "fulu"
    assert doc["data"]["message"]["slot"] == path.stem
    unsigned_json = json.dumps(doc["data"]["message"], separators=(",", ":")).encode()
    proposal_json = json.dumps(
        {"data": {"block": doc["data"]["message"], "kzg_proofs": [], "blobs": []}},
        separators=(",", ":"),
    ).encode()
    codec = ssz_z.get_type("BeaconBlockContents", fork="fulu", preset="mainnet")
    proposal_ssz = codec.load_json(proposal_json, wrapped=True).to_ssz()
    cases.append(
        (
            path.stem,
            js,
            ss,
            proposal_json,
            proposal_ssz,
            unsigned_json,
            bytes.fromhex(doc["data"]["signature"][2:]),
        )
    )
    metadata["inputs"].append(
        {
            "slot": path.stem,
            "json_sha256": hashlib.sha256(js).hexdigest(),
            "ssz_sha256": hashlib.sha256(ss).hexdigest(),
        }
    )
assert cases
print(f"Preloaded {len(cases)} Fulu blocks", flush=True)


def run(case, order):
    slot, js, ss, proposal_json, proposal_ssz, unsigned_json, signature = case
    elapsed, outputs = {}, {}
    for label in order:
        module, block_class = libs[label]
        signed_codec = module.get_type("SignedBeaconBlock", fork="fulu", preset="mainnet")
        proposal_codec = module.get_type("BeaconBlockContents", fork="fulu", preset="mainnet")

        def timed(metric, callback):
            start = time.perf_counter_ns()
            result = callback()
            elapsed[label, metric] = time.perf_counter_ns() - start
            return result

        value = timed("json_decode", lambda: signed_codec.load_json(js, wrapped=True))
        json_output = timed("json_encode", value.to_json)
        assert value.to_ssz() == ss
        value = timed("ssz_decode", lambda: signed_codec.load_ssz(ss))
        assert timed("ssz_encode", value.to_ssz) == ss
        root = timed("object_to_root", value.hash_tree_root)
        assert timed("ssz_to_root", lambda: signed_codec.hash_tree_root_from_ssz(ss)) == root

        def proposal(wire):
            value = (
                proposal_codec.load_json(proposal_json, wrapped=True)
                if wire == "json"
                else proposal_codec.load_ssz(proposal_ssz)
            )
            block = block_class(value)
            header = block.header_dict()
            signed = block.sign(signature).value
            encoded = signed.to_json() if wire == "json" else signed.to_ssz()
            return header, block.block_hash_tree_root(), encoded

        json_flow = timed("proposal_json", lambda: proposal("json"))
        ssz_flow = timed("proposal_ssz", lambda: proposal("ssz"))
        assert json_flow[:2] == ssz_flow[:2]
        # Measure signing and root retrieval separately to expose cache behavior.
        unsigned = module.get_type("BeaconBlock", fork="fulu", preset="mainnet").load_json(
            unsigned_json
        )
        unsigned.hash_tree_root()
        signed = timed("sign_hashed_block", lambda: unsigned.sign(signature))
        signed_root = timed("signed_root_after_sign", signed.hash_tree_root)
        assert signed_root == signed.codec.hash_tree_root_from_ssz(signed.to_ssz())
        outputs[label] = (
            root,
            json.loads(json_output),
            json_flow[:2],
            json.loads(json_flow[2]),
            ssz_flow,
            signed_root,
        )
    assert outputs["before"] == outputs["after"], slot
    return elapsed


for case in cases[:: max(1, len(cases) // 12)][:12]:
    run(case, ("before", "after"))
gc.collect()
rows = []
gc.disable()
try:
    for round_index in range(args.rounds):
        start = time.perf_counter()
        for index, case in enumerate(cases):
            order = ("before", "after") if (index + round_index) % 2 == 0 else ("after", "before")
            for (label, metric), ns in run(case, order).items():
                rows.append((round_index + 1, case[0], label, metric, ns))
        print(
            f"Pass {round_index + 1}/{args.rounds}: {time.perf_counter() - start:.1f}s", flush=True
        )
    for name in ("BeaconBlock", "SignedBeaconBlock", "BeaconState"):
        codecs = {
            label: module.get_type(name, fork="fulu", preset="mainnet")
            for label, (module, _) in libs.items()
        }
        for codec in codecs.values():
            codec.default()
        for round_index in range(args.rounds):
            for index in range(10):
                order = (
                    ("before", "after") if (index + round_index) % 2 == 0 else ("after", "before")
                )
                values = {}
                for label in order:
                    start = time.perf_counter_ns()
                    values[label] = codecs[label].default().to_ssz()
                    rows.append(
                        (
                            round_index + 1,
                            name,
                            label,
                            "default_" + name,
                            time.perf_counter_ns() - start,
                        )
                    )
                assert values["before"] == values["after"]
finally:
    gc.enable()

with (args.output / "samples.csv").open("w", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("round", "slot_or_type", "library", "metric", "nanoseconds"))
    writer.writerows(rows)
groups = defaultdict(lambda: defaultdict(list))
for round_index, _, label, metric, ns in rows:
    groups[metric, label][round_index].append(ns)
results = {}
for metric in dict.fromkeys(row[3] for row in rows):
    result = {}
    for label in libs:
        passes = groups[metric, label]
        xs = sorted(x for values in passes.values() for x in values)
        means = [statistics.mean(values) / 1e6 for values in passes.values()]
        result[label] = {
            "ms_per_block": statistics.median(means),
            "pass_means_ms": means,
            "p50_ms": statistics.median(xs) / 1e6,
            "p95_ms": xs[int((len(xs) - 1) * 0.95)] / 1e6,
        }
    result["after_over_before"] = result["after"]["ms_per_block"] / result["before"]["ms_per_block"]
    results[metric] = result
    print(
        f"{metric}: before={result['before']['ms_per_block']:.6f} ms, "
        f"after={result['after']['ms_per_block']:.6f} ms, "
        f"after/before={result['after_over_before']:.3f}",
        flush=True,
    )
summary = {"metadata": metadata, "blocks": len(cases), "results": results}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
