#!/usr/bin/env bash
# Scenario One (Traffic Steering, live RIC). 사용법: ./run_s1.sh [simTime]
SIMTIME=${1:-10}
cd "$(dirname "$0")"
: > ts_actions_for_ns3.csv
echo ">> scenario-one 실행 (simTime=${SIMTIME}, e2TermIp=10.0.2.10)"
./waf --run "scratch/scenario-one \
  --RngRun=1 --enableTraces=1 --e2lteEnabled=1 --e2nrEnabled=1 \
  --e2du=1 --e2cuUp=1 --e2cuCp=1 --reducedPmValues=1 \
  --simTime=${SIMTIME} --outageThreshold=-1000 --handoverMode=NoAuto \
  --numberOfRaPreambles=20 --e2TermIp=10.0.2.10 --enableE2FileLogging=0 \
  --indicationPeriodicity=0.1 --controlFileName=ts_actions_for_ns3.csv"
