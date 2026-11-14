import { createHash, randomUUID } from 'node:crypto';

function actionOf(proposal) {
  if (!proposal || typeof proposal !== 'object') throw new Error('invalid proposal');
  const { contract_id, receiver_id, amount, nonce } = proposal;
  if (typeof contract_id !== 'string' || !contract_id) throw new Error('invalid contract');
  if (typeof receiver_id !== 'string' || !receiver_id) throw new Error('invalid receiver');
  if (typeof nonce !== 'string' || !nonce || nonce.length > 64) throw new Error('invalid nonce');
  if (typeof amount !== 'string' || !/^[1-9][0-9]*$/.test(amount)) throw new Error('invalid amount');
  return { contract_id, receiver_id, amount, nonce };
}

function digest(action) {
  const fields = [action.contract_id, 'execute', action.receiver_id, action.amount, action.nonce];
  return createHash('sha256').update('near-receipt-guard/v1\0').update(JSON.stringify(fields)).digest('hex');
}

// The trusted application passes a signer once and exposes only this guard to the agent.
export function createGuard(contract, signer) {
  if (typeof signer !== 'function') throw new Error('signer required');
  const receipts = new Map();
  return {
    async preflight(proposal) {
      const action = actionOf(proposal);
      if (action.contract_id !== contract.accountId) return { decision: 'block', reason: 'contract changed' };
      const [allowed, callLimit, remaining] = await Promise.all([
        contract.view('is_allowed', { receiver_id: action.receiver_id }),
        contract.view('per_call_limit', {}),
        contract.view('remaining_today', {}),
      ]);
      if (!allowed) return { decision: 'block', reason: 'receiver blocked' };
      if (BigInt(action.amount) > BigInt(callLimit)) return { decision: 'block', reason: 'per-call limit exceeded' };
      if (BigInt(action.amount) > BigInt(remaining)) return { decision: 'block', reason: 'daily limit exceeded' };
      const receiptId = randomUUID();
      const sha256 = digest(action);
      receipts.set(receiptId, sha256);
      return { decision: 'allow', receiptId, sha256 };
    },
    async commit(receiptId, currentProposal) {
      const expected = receipts.get(receiptId);
      if (!expected) throw new Error('unknown or spent receipt');
      receipts.delete(receiptId);
      const action = actionOf(currentProposal);
      if (digest(action) !== expected) throw new Error('proposal changed after preflight');
      // The trusted signer is reached only after the exact proposal passes the receipt check.
      return signer(action);
    },
  };
}
