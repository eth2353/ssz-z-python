"""Run a small Gloas SSZ example after installing the package."""

from ssz_z import get_type


def main():
    codec = get_type("SignedBeaconBlock", fork="gloas", preset="mainnet")
    block = codec.default()
    encoded = block.to_ssz()
    assert codec.load_ssz(encoded) == block
    assert codec.load_json(block.to_json()) == block
    print(f"SSZ bytes: {len(encoded)}")
    print(f"Hash tree root: 0x{block.hash_tree_root().hex()}")


if __name__ == "__main__":
    main()
