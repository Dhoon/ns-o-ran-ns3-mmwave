#!/usr/bin/env bash
# Measure how many concurrent scenario-one runs give the best throughput on this machine.
# Runs N copies of a short sim (6 UEs/gNB, real-run flags) for each N, one batch at a time.
# Usage: measure_parallel_throughput.sh ["1 8 12 16"]
set -uo pipefail

NSORAN="${NSORAN:-$HOME/research/nsoran/ns-o-ran-ns3-mmwave}"
BIN="$NSORAN/build/optimized/scratch/ns3.38.rc1-scenario-one-optimized"
OUT="${OUT:-$NSORAN/ns-o-ran-security/results/raw/throughput}"
NLIST="${1:-1 8 12 16}"
SIM="${SIM:-0.5}"

export LD_LIBRARY_PATH="$NSORAN/build/optimized/lib:$NSORAN/build/lib:${LD_LIBRARY_PATH:-}"
rm -rf "$OUT"; mkdir -p "$OUT"

one() {  # N index
    local dir="$OUT/N$1/r$2"
    mkdir -p "$dir"; : > "$dir/ts_actions_for_ns3.csv"
    ( cd "$dir" && /usr/bin/time -f "%e %M" -o time.txt "$BIN" --configuration=0 --ues=6 \
        --trafficModel=3 --handoverMode=Threshold --hoSinrDifference=3 --outageThreshold=-5.0 \
        --minSpeed=2 --maxSpeed=4 --indicationPeriodicity=0.1 --enableE2FileLogging=1 \
        --enableTraces=1 --simTime="$SIM" --RngRun="$2" > run.log 2>&1 )
}

echo "N  mean_wall_s  min  max  maxRSS_MB  sim-s_per_wall-hour  speedup_vs_first"
base=""
for N in $NLIST; do
    t0=$(date +%s)
    for i in $(seq 1 "$N"); do one "$N" "$i" & done
    wait
    T=$(( $(date +%s) - t0 ))
    stats=$(cat "$OUT"/N"$N"/r*/time.txt | awk '{s+=$1; if(min==""||$1<min)min=$1; if($1>max)max=$1; if($2>m)m=$2}
        END{printf "%.0f %.0f %.0f %.0f", s/NR, min, max, m/1024}')
    thr=$(awk -v n="$N" -v sim="$SIM" -v t="$T" 'BEGIN{printf "%.2f", n*sim/t*3600}')
    [ -z "$base" ] && base=$thr
    echo "$N  $stats  $thr  $(awk -v a="$thr" -v b="$base" 'BEGIN{printf "%.2f", a/b}')"
done
