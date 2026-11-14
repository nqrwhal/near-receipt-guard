use std::collections::BTreeSet;

use near_sdk::json_types::U128;
use near_sdk::{env, near, require, AccountId, NearToken, PanicOnDefault, Promise};

const DAY_NS: u64 = 86_400_000_000_000;
const MIN_RESERVE_YOCTO: u128 = 1_000_000_000_000_000_000_000_000;

#[near(contract_state)]
#[derive(PanicOnDefault)]
pub struct ReceiptGuard {
    allowed_receivers: Vec<AccountId>,
    per_call_limit: u128,
    daily_limit: u128,
    spent_day: u64,
    spent_today: u128,
    used_nonces: BTreeSet<String>,
}

#[near]
impl ReceiptGuard {
    #[init]
    pub fn new(allowed_receivers: Vec<AccountId>, per_call_limit: U128, daily_limit: U128) -> Self {
        require!(!allowed_receivers.is_empty(), "at least one receiver required");
        require!(per_call_limit.0 > 0, "per-call limit must be positive");
        require!(daily_limit.0 >= per_call_limit.0, "daily limit must cover one call");
        let mut unique = BTreeSet::new();
        for receiver in &allowed_receivers {
            require!(unique.insert(receiver.clone()), "duplicate receiver");
        }
        Self {
            allowed_receivers,
            per_call_limit: per_call_limit.0,
            daily_limit: daily_limit.0,
            spent_day: env::block_timestamp() / DAY_NS,
            spent_today: 0,
            used_nonces: BTreeSet::new(),
        }
    }

    /// Called with a function-call key scoped to this contract and this method.
    /// The agent key cannot transfer NEAR directly or change this policy.
    pub fn execute(&mut self, receiver_id: AccountId, amount: U128, nonce: String) -> Promise {
        require!(
            env::predecessor_account_id() == env::current_account_id(),
            "only this account may execute"
        );
        require!(self.allowed_receivers.contains(&receiver_id), "receiver blocked");
        require!(amount.0 > 0 && amount.0 <= self.per_call_limit, "per-call limit exceeded");
        require!(!nonce.is_empty() && nonce.len() <= 64, "invalid nonce");
        require!(!self.used_nonces.contains(&nonce), "nonce replay");

        let day = env::block_timestamp() / DAY_NS;
        if day != self.spent_day {
            self.spent_day = day;
            self.spent_today = 0;
        }
        let next_spent = self.spent_today.checked_add(amount.0).expect("spend overflow");
        require!(next_spent <= self.daily_limit, "daily limit exceeded");
        let min_balance = amount.0.checked_add(MIN_RESERVE_YOCTO).expect("balance overflow");
        require!(
            env::account_balance().as_yoctonear() >= min_balance,
            "insufficient treasury balance"
        );

        self.spent_today = next_spent;
        self.used_nonces.insert(nonce);
        Promise::new(receiver_id).transfer(NearToken::from_yoctonear(amount.0))
    }

    pub fn per_call_limit(&self) -> U128 {
        U128(self.per_call_limit)
    }

    pub fn remaining_today(&self) -> U128 {
        let day = env::block_timestamp() / DAY_NS;
        if day == self.spent_day {
            U128(self.daily_limit - self.spent_today)
        } else {
            U128(self.daily_limit)
        }
    }

    pub fn is_allowed(&self, receiver_id: AccountId) -> bool {
        self.allowed_receivers.contains(&receiver_id)
    }
}
