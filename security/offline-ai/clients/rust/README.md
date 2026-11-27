# Offline Rust DLP adapter — unqualified

The Rust client uses a Unix-domain socket to the same Python Presidio/GLiNER
DLP broker as the Node client. It does not use HTTP, DNS or an external API.

The caller must start the broker under a privately owned directory, with mode
0700, and the socket must be mode 0600. The payload and response are bounded to
1 MiB. All transport, serialization and broker errors become `DLP_REJECTED`
without exposing raw data.

To qualify in an approved offline Rust environment:

1. Vendor and audit the exact `serde_json` version and transitive crates.
2. Generate and commit an approved Cargo.lock.
3. Run `cargo test --offline --locked`, formatting, Clippy and cargo audit
   using only locally provisioned tools/advisories.
4. Test end-to-end against the real Python broker and GLiNER model.
5. Integrate the wrapper at each source-to-sink boundary, including agent inputs,
   retrieval, MCP and tool responses, logging and external egress.

**This crate has not been compiled in this session.** Its source and tests are a
draft contract, not production assurance.
