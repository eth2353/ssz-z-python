# ruff: noqa: E402, B023
# Paths precede optional imports; timed callbacks are invoked synchronously inside each loop.
"""Compare the saved spy-ssz pin with the optimized SSZ bindings on the same corpus.

Use Vero's Python interpreter and pass the site-packages directory containing
its original spy-ssz build. No packages or repository files are modified.
"""

import argparse
import csv
import gc
import hashlib
import importlib.metadata
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--corpus", type=Path, required=True)
parser.add_argument("--spy-site-packages", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--rounds", type=int, default=3)
parser.add_argument("--limit", type=int, default=0)
args = parser.parse_args()
sys.path.append(str(args.spy_site_packages))


import spy_ssz
from spy_ssz import Fork as SpyFork
from spy_ssz import ObjectKind, get_ssz_type

from ssz_z import get_type
from ssz_z.beacon_api import BlockValue

METRICS = (
    "json_decode",
    "json_encode",
    "ssz_decode",
    "ssz_encode",
    "object_to_root",
    "ssz_to_root",
    "proposal_json",
    "proposal_ssz",
)
metadata = {
    "python": sys.version,
    "platform": platform.platform(),
    "spy_module": spy_ssz.__file__,
    "corpus": str(args.corpus),
    "rounds": args.rounds,
    "limit": args.limit,
    "mode": "native",
    "timer": "perf_counter_ns",
    "method": "Sequential, interleaved old/new; alternate order by block and round; "
    "12 warmup blocks/network; inputs in RAM; GC disabled; validation outside timers.",
    "proposal_flow": "Decode unsigned production response -> header -> attach original "
    "signature -> publish encoding -> block root. Fulu contents are "
    "constructed from real blocks with empty blobs/proofs because these "
    "are absent from the corpus. Gloas uses original unsigned block.",
}
for name in ("spy-ssz", "ssz-z-python"):
    dist = importlib.metadata.distribution(name)
    metadata[name] = {
        "version": dist.version,
        "source": json.loads(dist.read_text("direct_url.json") or "null"),
    }
import subprocess

import ssz_z

metadata["ssz_z_import"] = ssz_z.__file__
metadata["ssz-z-python"]["runtime_version"] = ssz_z.__version__
metadata["ssz_z_source_base"] = (
    subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(ssz_z.__file__).parents[2])
    .decode()
    .strip()
)
source_root = Path(ssz_z.__file__).parents[2]
source_files = [
    *Path(ssz_z.__file__).parent.glob("*.py"),
    *source_root.glob("native/*.zig"),
    source_root / "build.zig",
    source_root / "pyproject.toml",
]
metadata["ssz_z_source_files_sha256"] = {
    str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(source_files)
}
metadata["ssz_z_native_files_sha256"] = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(Path(ssz_z.__file__).parent.glob("_native/*"))
    if p.suffix in {".dylib", ".so", ".dll"}
}
assert Path(spy_ssz.__file__).resolve().is_relative_to(args.spy_site_packages.resolve())
assert (
    metadata["spy-ssz"]["source"]["vcs_info"]["commit_id"]
    == "612c3f73c54ff2a8cbc374f5c4af7b9d7aa24d00"
)

args.output.mkdir(parents=True, exist_ok=True)
(args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
summary = {"metadata": metadata, "networks": {}}

with (args.output / "samples.csv").open("w", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(["network", "fork", "round", "slot", "library", "metric", "nanoseconds"])
    for network in ("mainnet", "hoodi", "gloas"):
        manifest = json.loads((args.corpus / network / "manifest.json").read_bytes())
        fork = manifest["fork"]
        entries = manifest["blocks"]
        if args.limit:
            entries = [
                entries[i * len(entries) // args.limit]
                for i in range(min(args.limit, len(entries)))
            ]
        cases = []
        for entry in entries:
            js = (args.corpus / network / entry["json"]).read_bytes()
            ss = (args.corpus / network / entry["ssz"]).read_bytes()
            assert hashlib.sha256(js).hexdigest() == entry["json_sha256"]
            assert hashlib.sha256(ss).hexdigest() == entry["ssz_sha256"]
            cases.append((str(entry["slot"]), js, ss))
        native = get_type("SignedBeaconBlock", fork=fork, preset="mainnet")
        old = get_ssz_type(SpyFork[fork.upper()], ObjectKind.SIGNED_BEACON_BLOCK)
        name = "BeaconBlock" if fork == "gloas" else "BeaconBlockContents"
        new_proposal = get_type(name, fork=fork, preset="mainnet")
        old_proposal = get_ssz_type(
            SpyFork[fork.upper()],
            ObjectKind.BEACON_BLOCK if fork == "gloas" else ObjectKind.BEACON_BLOCK_CONTENTS,
        )
        totals = defaultdict(lambda: defaultdict(float))
        samples = defaultdict(list)
        print(f"{network}: preloaded and verified {len(cases)} blocks; fork={fork}", flush=True)

        def run(case, order):
            slot, json_input, ssz_input = case
            signed_value = json.loads(json_input)["data"]
            value = signed_value["message"]
            if fork != "gloas":
                value = {"block": value, "kzg_proofs": [], "blobs": []}
            production_json = json.dumps({"data": value}, separators=(",", ":")).encode()
            production_ssz = new_proposal.load_json(
                json.dumps(value, separators=(",", ":")).encode()
            ).to_ssz()
            signature = signed_value["signature"]
            output = {}
            elapsed = {}

            def timed(lib, metric, func):
                start = time.perf_counter_ns()
                result = func()
                elapsed[lib, metric] = time.perf_counter_ns() - start
                return result

            def proposal(lib, wire):
                if lib == "spy-ssz":
                    obj = (
                        old_proposal.from_json(production_json)
                        if wire == "json"
                        else old_proposal.from_ssz(production_ssz)
                    )
                    try:
                        header = obj.header_dict()
                        with obj.sign(signature) as signed:
                            encoded = signed.to_json() if wire == "json" else signed.to_ssz()
                        root = obj.block_hash_tree_root()
                        return header, root, encoded
                    finally:
                        obj.close()
                obj = (
                    new_proposal.load_json(production_json, wrapped=True)
                    if wire == "json"
                    else new_proposal.load_ssz(production_ssz)
                )
                obj = BlockValue(obj)
                header = obj.header_dict()
                signed = obj.sign(signature).value
                encoded = signed.to_json() if wire == "json" else signed.to_ssz()
                return header, "0x" + obj.block_hash_tree_root().hex(), encoded

            def old_ssz_root():
                with old.from_ssz(ssz_input) as obj:
                    return obj.hash_tree_root()

            for lib in order:
                if lib == "spy-ssz":
                    obj = timed(lib, "json_decode", lambda: old.from_json(json_input))
                    try:
                        json_output = timed(lib, "json_encode", obj.to_json)
                        assert obj.to_ssz() == ssz_input
                    finally:
                        obj.close()
                    obj = timed(lib, "ssz_decode", lambda: old.from_ssz(ssz_input))
                    try:
                        assert timed(lib, "ssz_encode", obj.to_ssz) == ssz_input
                        root = timed(lib, "object_to_root", obj.hash_tree_root)
                    finally:
                        obj.close()
                    direct_root = timed(lib, "ssz_to_root", old_ssz_root)
                else:
                    obj = timed(
                        lib, "json_decode", lambda: native.load_json(json_input, wrapped=True)
                    )
                    json_output = timed(lib, "json_encode", obj.to_json)
                    assert obj.to_ssz() == ssz_input
                    obj = timed(lib, "ssz_decode", lambda: native.load_ssz(ssz_input))
                    assert timed(lib, "ssz_encode", obj.to_ssz) == ssz_input
                    root = timed(lib, "object_to_root", obj.hash_tree_root)
                    direct_root = timed(
                        lib, "ssz_to_root", lambda: native.hash_tree_root_from_ssz(ssz_input)
                    )
                assert direct_root == root
                json_flow = timed(lib, "proposal_json", lambda: proposal(lib, "json"))
                ssz_flow = timed(lib, "proposal_ssz", lambda: proposal(lib, "ssz"))
                assert json_flow[:2] == ssz_flow[:2]
                output[lib] = (root, json_flow, ssz_flow, json_output)
            a, b = output["spy-ssz"], output["ssz-z-python"]
            assert json.loads(a[3]) == json.loads(b[3]), (
                network,
                slot,
                "JSON encode mismatch",
            )
            assert a[0] == b[0], (network, slot, "signed root mismatch")
            assert a[1][:2] == b[1][:2], (network, slot, "header/block root mismatch")
            assert json.loads(a[1][2]) == json.loads(b[1][2]), (
                network,
                slot,
                "signed JSON mismatch",
            )
            assert a[2] == b[2], (network, slot, "signed SSZ mismatch")
            return elapsed

        for index in range(min(12, len(cases))):
            run(cases[index * len(cases) // min(12, len(cases))], ("spy-ssz", "ssz-z-python"))
        gc.collect()
        gc.disable()
        try:
            for round_index in range(args.rounds):
                start = time.perf_counter()
                for index, case in enumerate(cases):
                    order = ("spy-ssz", "ssz-z-python")
                    if (index + round_index) % 2:
                        order = order[::-1]
                    if index and index % 250 == 0:
                        print(
                            f"{network}: pass {round_index + 1}, {index}/{len(cases)} blocks",
                            flush=True,
                        )
                    for (lib, metric), ns in run(case, order).items():
                        writer.writerow([network, fork, round_index + 1, case[0], lib, metric, ns])
                        totals[lib, metric][round_index] += ns
                        samples[lib, metric].append(ns)
                stream.flush()
                print(
                    f"{network}: pass {round_index + 1}/{args.rounds} complete "
                    f"in {time.perf_counter() - start:.1f}s",
                    flush=True,
                )
        finally:
            gc.enable()
        records = {}
        for metric in METRICS:
            records[metric] = {}
            for lib in ("spy-ssz", "ssz-z-python"):
                xs = sorted(samples[lib, metric])
                means = [total / len(cases) / 1e6 for total in totals[lib, metric].values()]
                records[metric][lib] = {
                    "ms_per_block": statistics.median(means),
                    "pass_means_ms": means,
                    "p50_ms": statistics.median(xs) / 1e6,
                    "p95_ms": xs[int((len(xs) - 1) * 0.95)] / 1e6,
                }
            records[metric]["ratio"] = (
                records[metric]["ssz-z-python"]["ms_per_block"]
                / records[metric]["spy-ssz"]["ms_per_block"]
            )
        summary["networks"][network] = {
            "fork": fork,
            "count": len(cases),
            "json_bytes": sum(len(c[1]) for c in cases),
            "ssz_bytes": sum(len(c[2]) for c in cases),
            "results": records,
        }
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        for metric, record in records.items():
            print(
                f"  {metric}: spy={record['spy-ssz']['ms_per_block']:.4f} ms, "
                f"zig={record['ssz-z-python']['ms_per_block']:.4f} ms, "
                f"ratio={record['ratio']:.2f}x",
                flush=True,
            )
