# Local patches

## Lodestar-Z progressive container compile-time quota

`lodestar-z/src/ssz/type/progressive_container.zig`: raise Zig's compile-time
branch quota to 100,000 inside the two `field_indices` constant initializers.
The 46-field Gloas BeaconState in consensus-specs v1.7.0-beta.4 exceeds Zig's
default quota of 1,000 branches when computing its progressive field indices.
This changes only compiler evaluation capacity; runtime behavior and SSZ
algorithms remain upstream's implementation.
