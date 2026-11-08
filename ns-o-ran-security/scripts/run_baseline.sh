#!/usr/bin/env bash
# Run scenario-one Traffic Steering, aligned baseline (guide sections 11, 14).
# Must be run from inside the ns-o-ran-ns3-mmwave tree with the RIC up.
set -euo pipefail

NSORAN="${NSORAN:-$HOME/research/nsoran/ns-o-ran-ns3-mmwave}"
E2TERM_IP="${E2TERM_IP:?set E2TERM_IP (docker inspect ... e2term)}"
SEED="${SEED:-1}"
SIMTIME="${SIMTIME:-1.0}"          # keep short until the pipeline is verified
UES="${UES:-3}"

cd "$NSORAN"
: > ts_actions_for_ns3.csv          # empty control file to avoid premature crash

./waf --run "scratch/scenario-one --RngRun=${SEED} \
  --configuration=0 --trafficModel=3 \
  --enableTraces=1 --e2lteEnabled=1 --e2nrEnabled=1 \
  --e2du=1 --e2cuUp=1 --e2cuCp=1 \
  --simTime=${SIMTIME} --outageThreshold=-1000 --handoverMode=NoAuto \
  --basicCellId=1 --ues=${UES} --reducedPmValues=0 \
  --e2TermIp=${E2TERM_IP} --enableE2FileLogging=1 \
  --minSpeed=2.0 --maxSpeed=4.0 --numberOfRaPreambles=20 \
  --indicationPeriodicity=0.1 --controlFileName=ts_actions_for_ns3.csv"
