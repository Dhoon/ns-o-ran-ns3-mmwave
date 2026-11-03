#!/usr/bin/env bash
# Scenario One, OFFLINE KPM dump (no RIC). 사용법: ./run_s1_offline.sh [simTime] [RngRun]
SIMTIME=${1:-5}
RUN=${2:-1}
cd "$(dirname "$0")"
: > ts_actions_for_ns3.csv
echo ">> scenario-one OFFLINE (simTime=${SIMTIME}, RngRun=${RUN}, enableE2FileLogging=1)"
./waf --run "scratch/scenario-one \
  --RngRun=${RUN} --enableTraces=1 --e2lteEnabled=1 --e2nrEnabled=1 \
  --e2du=1 --e2cuUp=1 --e2cuCp=1 --reducedPmValues=0 \
  --simTime=${SIMTIME} --outageThreshold=-1000 --handoverMode=NoAuto \
  --numberOfRaPreambles=20 --enableE2FileLogging=1 \
  --indicationPeriodicity=0.1 --controlFileName=ts_actions_for_ns3.csv"
echo ">> 완료. 생성된 KPM/트레이스 파일:"
ls -lt *.txt *.csv 2>/dev/null | head -20
