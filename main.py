"""Run a small Gloas SSZ example after installing the package."""

from ssz_z import get_type


def main():
    codec = get_type("SignedBeaconBlock", fork="gloas", preset="mainnet")
    block = codec.default()
    block["message"]["slot"] = 123
    encoded = codec.serialize(block)
    assert codec.deserialize(encoded) == block
    print(f"SSZ bytes: {len(encoded)}")
    print(f"Hash tree root: 0x{codec.hash_tree_root_from_ssz(encoded).hex()}")


if __name__ == "__main__":
    main()
