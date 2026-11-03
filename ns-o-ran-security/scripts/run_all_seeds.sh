#!/usr/bin/env bash
# Paired aligned/attack sweep across seeds (guide section 27).
# Keeps topology, trajectories, traffic, and policy weights fixed; only the
# RngRun and the attack mode vary.
set -euo pipefail

SEEDS="${SEEDS:-1 2 3 4 5}"
MODES="${MODES:-baseline uniform_lag feature_lag selective_attack}"

for seed in $SEEDS; do
  for mode in $MODES; do
    echo "=== seed=${seed} mode=${mode} ==="
    SEED="$seed" CONFIG="configs/${mode}.yaml" \
      bash "$(dirname "$0")/run_attack.sh" || {
        echo "run failed: seed=${seed} mode=${mode}" >&2; exit 1; }
  done
done
