# External and large-data retrieval contract

`config/fetch_manifest.csv` is the authoritative list of material that cannot
yet be embedded as small canonical files. Empty locator, checksum or licence
fields are deliberate blockers, not optional metadata.

Before a fetch target can become available:

1. record a stable accession, immutable URL or preserved collaborator intake;
2. record the exact version, byte size and SHA-256 checksum;
3. record the licence or reuse permission;
4. fetch into `data/raw/` or `data/external/` without changing the supplied bytes;
5. verify the checksum before extraction or analysis;
6. keep network retrieval separate from the offline reproduction phase.

Raw packages received directly from collaborators must first pass through
`tools/intake_external_package.py`. The intake archive remains unchanged under
`archive/incoming/`; canonical analysis operates on a verified working copy.
