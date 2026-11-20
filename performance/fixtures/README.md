Fulu mainnet signed beacon block at slot 13,689,080, selected as the largest
JSON document in the supplied `/tmp/beacon_blocks` corpus. The JSON retains its
Beacon API envelope; the SSZ file encodes its `data` SignedBeaconBlock.

`performance/regression.py` verifies JSON/SSZ equivalence before timing. CI
compares nine warmed-up batch medians against the PR base or previous master
commit on the same runner. A regression requires both a 50% increase and an
absolute increase above 10 microseconds. Hashing bypasses the value root cache;
SSZ encoding measures the public API's retained-byte retrieval.

Results appear in the workflow summary. These measurements cover one large
block without blob contents; they are a coarse regression guard, not a stable
cross-machine benchmark.
