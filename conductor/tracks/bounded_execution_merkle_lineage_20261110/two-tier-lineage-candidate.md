# Two-tier lineage candidate — 27 November 2026

Refs #19 and #192, existing B02 track. Read-only reconciliation with
tobac at fe06ef5958ba0f218317a738fe8de95973300a12 and archive-govt-nz at
a17b5cf537f06fcd5bce977854da40e51a059c81 confirms the two-tier objective
and sorted artifact_id/raw_bytes_sha256/extract_sha256 leaf structure.
No consumer code or schema is modified. The exact shared byte encoding
is not yet qualified; use the explicit candidate algorithm version, not
an asserted consumer-compatible format.

Bounded synthetic staged-byte manifest v1 uses SHA-256 over canonical
sorted runner path/digest pairs prefixed by closure plus NUL. Registry
leaves hash leaf plus NUL and canonical sorted triples; internal pairs
hash node plus NUL and their two binary digests, promoting an unpaired
last node. UTF-8 JSON uses sorted keys, compact separators and no nonfinite
values. Independent raw-manifest digest binds path and dependency metadata
that are not included in the triple root. Both inventories are complete
and disjoint; verify every byte, reject aliases, missing or extra paths,
substituted manifests, unknown or cyclic declared dependencies. No raw
filesystem reads or traversal; caller stages bytes independently.
Limits: 256 rows per tier, 1 MiB manifest, 32 MiB staged bytes. Five local
synthetic methods passed. This is a byte-fixity and declared-DAG check, not
a proof of implicit byte-level cycles, source authenticity, completeness
of an external inventory, extracted-cell correctness or scientific truth.
Downstream encoding parity, original-to-extract coordinate verification,
actual signed artifacts and full hosted qualification remain open.
