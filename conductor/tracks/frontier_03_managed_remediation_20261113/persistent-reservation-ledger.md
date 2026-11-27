# Persistent advisory reservation ledger — 27 November 2026

Refs #24 and #192. #199 merged at af84c5a0e32fae5632b162fa21d482e837c6ca23.
#200 refreshed head 275dcc8ebac61e7549314ce49429d0a1ab009471 passed eight
checks and completed independent review; merged at
e2c96c2da46e7f0804a50711f82ff1b9889ad053. Its combined policy job 140503070718
reported 387 tests, 349 passed, 38 existing capability skips; all five observed
receiving-main checks passed.

Use the existing additive plan contract before recording any advisory
reservation. A single local SQLite transaction serializes checks and inserts;
numeric repository ID (independently bound by a trusted caller) and portable
path identify a reservation across reissued plans, changed expiry/head and
repository renames. Identical operations are already_recorded, different blob
or path collisions reject, partial overlap rejects atomically, and lock
contention fails closed. Persistent state is a reservation only; not a
successful operation or permission to apply. No automatic release or expiry
cleanup, distributed ledger, trusted live identity acquisition or writer.
The database must reside in a caller-controlled private directory; never
publish its contents. Recovery and authenticated snapshot binding remain
gated. Synthetic fixtures only.

Local TDD: seven methods passed on Python 3.13.5 using real SQLite databases
after an initial missing-module failure. Source contract Git blob
211320d209a84f3e32dd718e3d8e1a7c9bf1f2ed matched the merged source. Test
reissued plans, rename identity, conflicting paths/blobs, atomic overlap,
invalid context, simultaneous reservations and a locked database. Hosted full
suite and independent review still required. Preserve #196's distinct hold
and its owned plan.md; do not activate App writes, automatic merges or rollout.
