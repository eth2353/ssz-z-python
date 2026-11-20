"""Measure one Fulu block; compare medians with a separately built revision."""

import argparse
import gc
import json
import statistics
import time
from pathlib import Path

from ssz_z import get_type

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--baseline", type=Path)
args = parser.parse_args()
codec = get_type("SignedBeaconBlock", fork="fulu", preset="mainnet")
wire = args.fixture.with_suffix(".ssz").read_bytes()
document = json.dumps(json.loads(args.fixture.with_suffix(".json").read_bytes())["data"]).encode()
value = codec.load_ssz(wire)
assert codec.load_json(document).to_ssz() == wire
root = value.hash_tree_root()
assert codec.hash_tree_root_from_ssz(wire) == root
operations = {
    "json_decode": lambda: codec.load_json(document),
    "json_encode": value.to_json,
    "ssz_decode": lambda: codec.load_ssz(wire),
    "ssz_encode": value.to_ssz,
    "hash_tree_root": lambda: codec.hash_tree_root_from_ssz(wire),
}
samples = {name: [] for name in operations}
for operation in operations.values():
    for _ in range(20):
        operation()
gc.disable()
try:
    for round_number in range(9):
        order = list(operations)
        if round_number % 2:
            order.reverse()
        for name in order:
            operation = operations[name]
            start = time.perf_counter()
            count = 0
            while time.perf_counter() - start < 0.15:
                operation()
                count += 1
            samples[name].append((time.perf_counter() - start) / count)
finally:
    gc.enable()
results = {name: statistics.median(times) for name, times in samples.items()}
args.output.write_text(json.dumps({"seconds": results, "samples": samples}, indent=2) + "\n")
if args.baseline:
    baseline = json.loads(args.baseline.read_text())["seconds"]
    failed = []
    for name, elapsed in results.items():
        ratio = elapsed / baseline[name]
        print(f"{name}: {elapsed * 1000:.4f} ms, {ratio:.2f}x baseline")
        # Tiny buffer retrieval timings are dominated by interpreter/runner noise.
        if ratio > 1.5 and elapsed - baseline[name] > 0.00001:
            failed.append(name)
    if failed:
        raise SystemExit("Performance regression: " + ", ".join(failed))
