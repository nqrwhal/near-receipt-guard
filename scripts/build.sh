#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
original_home=${HOME:-}
if [ -n "$original_home" ]; then
  export RUSTUP_HOME="${RUSTUP_HOME:-$original_home/.rustup}"
  export CARGO_HOME="${CARGO_HOME:-$original_home/.cargo}"
fi
export HOME="$project_dir/.home"
export XDG_CONFIG_HOME="$project_dir/.home/.config"
mkdir -p "$XDG_CONFIG_HOME"
export PATH="$project_dir/node_modules/.bin:$PATH"
export CARGO_TARGET_DIR="$project_dir/target"
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
cd "$project_dir/contract"
cargo near build non-reproducible-wasm --locked --no-abi
mkdir -p "$project_dir/build"
cp "$project_dir/target/near/near_receipt_guard.wasm" "$project_dir/build/near_receipt_guard.wasm"
chmod 644 "$project_dir/build/near_receipt_guard.wasm"
