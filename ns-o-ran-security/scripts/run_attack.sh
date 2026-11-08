#!/usr/bin/env bash
# Placeholder attack-run entry point (guide sections 24, 34).
# Wiring note: the temporal-misalignment logic lives in the authorized xApp
# (xapp/*.py), applied at state construction. This script is the hook for
# launching an xApp configured by CONFIG together with the scenario-one run.
# It must NOT modify KPM values, authorization, or the control privilege.
set -euo pipefail

CONFIG="${CONFIG:?set CONFIG=configs/<mode>.yaml}"
SEED="${SEED:-1}"

echo "Would launch xApp with CONFIG=${CONFIG} SEED=${SEED}"
echo "TODO: bind AttackController(AttackConfig from ${CONFIG}) into the xApp"
echo "      KPM callback (guide sections 16 P1-P5, 17), then start scenario-one"
echo "      via run_baseline.sh with the same seed."
