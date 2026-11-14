# NEAR Receipt Guard

A local prototype for the [NEAR HACKATHON AI Security & Defense track](https://nearhackathon.com/). It lets an agent request a NEAR payment while a contract enforces a fixed receiver allowlist, per-call and UTC-day limits, and nonce replay protection. A small agent-side wrapper binds a preflight decision to the exact contract, method, receiver, amount, and nonce before the trusted signer runs.

This project has **only run on a local NEAR Sandbox**. The tests generate temporary simulated accounts and keys, send simulated NEAR, then remove the sandbox state. No mainnet or testnet account, wallet, transaction, submission, or social post was created.

## Run the local proof

On Linux, install Node.js 22.22.2 or newer, Rust with the `wasm32-unknown-unknown` target, and `npm ci`. Download the [official NEAR Sandbox 2.13.4 Linux x86_64 build](https://s3-us-west-1.amazonaws.com/build.nearprotocol.com/nearcore/Linux-x86_64/2.13.4/near-sandbox.tar.gz), extract it, then run:

```sh
export NEAR_SANDBOX_BINARY_PATH=/absolute/path/to/extracted/Linux-x86_64
./scripts/build.sh
./scripts/test-local.sh
```

The checked-in `build/near_receipt_guard.wasm` lets you omit the build command if you only want to run the tests. The test starts a temporary local chain, creates simulated accounts, deploys the contract, and checks an allowed payment plus blocked receiver, overspend, replay, proposal mutation, and direct transfer. It should finish with **7 passed, 0 failed**; `test-output.txt` records the last complete run. Expected contract panics are rejected transactions. The test removes its generated Sandbox state afterward and sends no mainnet or testnet transaction.

`cargo-near` 0.23.0 is pinned in `package-lock.json`; `near-sdk` 5.30.1 is pinned in `contract/Cargo.lock`. `near-workspaces` 5.0.0 otherwise downloads an older Sandbox binary incompatible with this contract, so set `NEAR_SANDBOX_BINARY_PATH` as shown. The build and test scripts keep generated files inside this project. The [52-second demo video](demo/near-receipt-guard-local-sandbox.mp4) shows the local architecture and saved test output.

## Design

`contract/src/lib.rs` is a Rust `near-sdk` contract. Its policy is fixed at initialization. It accepts `execute` only when the predecessor is the contract's own account. The test puts a function-call key on that account, scoped to `execute`; the agent never receives its full-access key. The contract checks receiver, amount, UTC-day total, nonce uniqueness, and a minimum treasury reserve before scheduling a transfer. Failed policy checks revert the call. [NEAR access keys](https://docs.near.org/protocol/accounts-contracts/access-keys) prevent the function-call key from making a direct NEAR transfer or calling other methods.

`guard.js` is the agent-side boundary. The trusted application supplies the signer once through `createGuard`; the agent gets only the resulting `preflight` and `commit` methods. `preflight` reads the contract's current allowlist and limits, then stores a SHA-256 digest of the exact proposal in trusted process memory. `commit` consumes that one-time receipt and recomputes the digest before invoking the private signer. If a prompt injection changes the recipient after preflight, the signer is never invoked. The contract still checks the policy if an agent bypasses this wrapper. The test in `test/guard.test.js` uses both layers and verifies actual Sandbox balances.

## Limits of this prototype

The wrapper assumes the agent controls proposal data but cannot edit its code, receipt map, or signer callback. The contract policy is immutable, and its `BTreeSet` of nonces grows over time. A failed asynchronous transfer after the contract schedules it would still consume the nonce and daily allowance; the demo uses existing local recipients and sufficient funds. These are production design items, not claims of a deployed wallet or a security audit.

## Authorship and reused work

Codex generated the Rust contract, JavaScript wrapper, Sandbox tests, scripts, and this README on November 13, 2026, under Yufei's direction. The project uses official `near-sdk`, `cargo-near`, `near-workspaces`, `near-api-js`, and NEAR Sandbox packages. It reuses a preexisting local Node toolchain and the general idea of comparing clean and altered SHA-256 digests from the Apart sprint harness created on November 12. **No Apart source, data, model output, or experiment result was copied.** If this project is entered, the README should retain that disclosure and clearly identify the NEAR work done during the hackathon window, as required by the [event rules on earlier code and AI work](https://nearhackathon.com/HACKATHON.md).

The code is [MIT licensed](LICENSE). A valid event submission additionally requires a human-published X demo video post, a mainnet NEAR payout address, contact details and consent, and submission by November 14, 2026 at 23:59 UTC. Publishing this repository alone does not enter the event.
