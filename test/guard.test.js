import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { rmSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { dirname, join } from 'node:path';

import { KeyPair, Worker } from 'near-workspaces';
import { functionCallAccessKey } from 'near-api-js/lib/transaction.js';
import { createGuard } from '../guard.js';

const PROJECT = dirname(dirname(fileURLToPath(import.meta.url)));
const WASM = join(PROJECT, 'build/near_receipt_guard.wasm');
const ONE = 10n ** 24n;
const proposal = (contract, receiver, amount, nonce) => ({
  contract_id: contract.accountId,
  receiver_id: receiver.accountId,
  amount: amount.toString(),
  nonce,
});
const balance = async account => BigInt((await account.accountView()).amount);

async function rejected(operation, expected) {
  let result;
  try {
    result = await operation();
  } catch (error) {
    assert.match(String(error), expected);
    return;
  }
  assert.equal(result.failed, true, 'transaction unexpectedly succeeded');
  assert.match(JSON.stringify(result.failure ?? result, (_key, value) =>
    typeof value === 'bigint' ? value.toString() : value), expected);
}

test('local NEAR agent spending guard', async t => {
  const sandboxHome = join(PROJECT, `.sandbox-${randomUUID()}`);
  let worker;
  try {
    worker = await Worker.init({ homeDir: sandboxHome, rm: false });
    const root = worker.rootAccount;
    const good = await root.createSubAccount('good');
    const bad = await root.createSubAccount('bad');
    const contract = await root.devDeploy(WASM, {
      initialBalance: 20n * ONE,
      method: 'new',
      args: {
        allowed_receivers: [good.accountId],
        per_call_limit: (2n * ONE).toString(),
        daily_limit: (3n * ONE).toString(),
      },
    });
    const agentKey = KeyPair.fromRandom('ed25519');
    const addKeyResult = await contract.batch(contract)
      .addKey(agentKey.getPublicKey(), functionCallAccessKey(contract.accountId, ['execute'], 2n * ONE))
      .transact();
    assert.equal(addKeyResult.failed, false);
    const signAndSend = action => contract.call(contract, 'execute', {
      receiver_id: action.receiver_id,
      amount: action.amount,
      nonce: action.nonce,
    }, { signWithKey: agentKey });
    const guard = createGuard(contract, signAndSend);
    const direct = (receiver, amount, nonce) => contract.callRaw(contract, 'execute', {
      receiver_id: receiver.accountId,
      amount: amount.toString(),
      nonce,
    }, { signWithKey: agentKey });

    await t.test('allowed payment uses scoped key and moves local funds', async () => {
      const before = await balance(good);
      const action = proposal(contract, good, ONE, 'allowed-1');
      const receipt = await guard.preflight(action);
      assert.equal(receipt.decision, 'allow');
      await guard.commit(receipt.receiptId, action);
      assert.equal((await balance(good)) - before, ONE);
      assert.equal(await contract.view('remaining_today', {}), (2n * ONE).toString());
    });

    await t.test('over-cap and blocked receiver fail on chain', async () => {
      assert.equal((await guard.preflight(proposal(contract, good, 3n * ONE, 'over-1'))).reason,
        'per-call limit exceeded');
      await rejected(() => direct(good, 3n * ONE, 'over-1'), /per-call limit exceeded/);
      assert.equal((await guard.preflight(proposal(contract, bad, ONE, 'bad-1'))).reason,
        'receiver blocked');
      await rejected(() => direct(bad, ONE, 'bad-1'), /receiver blocked/);
      assert.equal(await contract.view('remaining_today', {}), (2n * ONE).toString());
    });

    await t.test('nonce replay fails on chain', async () => {
      await rejected(() => direct(good, ONE, 'allowed-1'), /nonce replay/);
      assert.equal(await contract.view('remaining_today', {}), (2n * ONE).toString());
    });

    await t.test('mutation is rejected before signer is invoked', async () => {
      const goodAction = proposal(contract, good, ONE, 'mutation-1');
      let signCalls = 0;
      const guardedSigner = createGuard(contract, async action => {
        signCalls += 1;
        return signAndSend(action);
      });
      const receipt = await guardedSigner.preflight(goodAction);
      assert.equal(receipt.decision, 'allow');
      const badAction = proposal(contract, bad, ONE, 'mutation-1');
      const badBalance = await balance(bad);
      await assert.rejects(() => guardedSigner.commit(receipt.receiptId, badAction),
        /proposal changed after preflight/);
      assert.equal(signCalls, 0);
      assert.equal(await balance(bad), badBalance);
      await assert.rejects(() => guardedSigner.commit(receipt.receiptId, goodAction),
        /unknown or spent receipt/);
    });

    await t.test('daily cap fails after two allowed payments', async () => {
      const action = proposal(contract, good, 2n * ONE, 'allowed-2');
      const receipt = await guard.preflight(action);
      assert.equal(receipt.decision, 'allow');
      await guard.commit(receipt.receiptId, action);
      assert.equal(await contract.view('remaining_today', {}), '0');
      assert.equal((await guard.preflight(proposal(contract, good, 1n, 'daily-1'))).reason,
        'daily limit exceeded');
      await rejected(() => direct(good, 1n, 'daily-1'), /daily limit exceeded/);
    });

    await t.test('scoped key cannot make a direct transfer', async () => {
      await rejected(() => contract.batch(bad).transfer(1n).transact(agentKey),
        /does not have enough permission|not allowed|InvalidAccessKey|RequiresFullAccess|full access key/);
    });
  } finally {
    if (worker) await worker.tearDown();
    rmSync(sandboxHome, { recursive: true, force: true });
  }
});
