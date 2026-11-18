# Local patches

None. The vendored native sources match the revisions in [UPSTREAM.json](UPSTREAM.json).

Lodestar now raises the progressive-container compile-time quota upstream, so
the previous quota patch is no longer needed. The bindings also use upstream's
`ProgressiveByteListType` and minimal preset `PTC_SIZE=16` directly.
