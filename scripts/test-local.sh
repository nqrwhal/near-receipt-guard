#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${NEAR_SANDBOX_BINARY_PATH:?Set NEAR_SANDBOX_BINARY_PATH to the directory with near-sandbox 2.13.4}"
export NEAR_SANDBOX_BIN_PATH=1
export HOME="$project_dir/.home"
export TMPDIR="$project_dir/tmp"
export XDG_CACHE_HOME="$project_dir/.home/cache"
export NEAR_WORKSPACES_NO_LOGS=true
mkdir -p "$HOME" "$TMPDIR"
cd "$project_dir"
npm test
