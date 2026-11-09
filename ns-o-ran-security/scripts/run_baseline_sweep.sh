#!/usr/bin/env bash
# Offline baseline sweep for the TMC 2024 reproduction (no RIC, no xApp).
# Reduced scope: 850 MHz, 6/9/12 UEs per gNB, RAN RRM/SON1/SON2, 10 seeds, 30 s.
# Resumable: runs with a DONE marker are skipped. Usage: run_baseline_sweep.sh [max_parallel]
set -uo pipefail

NSORAN="${NSORAN:-$HOME/research/nsoran/ns-o-ran-ns3-mmwave}"
BIN="$NSORAN/build/optimized/scratch/ns3.38.rc1-scenario-one-optimized"
OUT="${OUT:-$NSORAN/ns-o-ran-security/results/raw/baseline}"
MAXPAR="${1:-16}"
SIMTIME="${SIMTIME:-30}"
SEEDS="${SEEDS:-$(seq 1 10)}"
UES_LIST="${UES_LIST:-12 9 6}"                     # heaviest first, so the long runs start at t=0
MODES="${MODES:-Threshold FixedTtt DynamicTtt}"    # RAN RRM, SON1, SON2
MIN_FREE_MB="${MIN_FREE_MB:-3000}"                 # do not start a job below this MemAvailable

export LD_LIBRARY_PATH="$NSORAN/build/optimized/lib:$NSORAN/build/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$OUT"
LOG="$OUT/progress.log"
COMMIT=$(git -C "$NSORAN" rev-parse --short HEAD)
DIRTY=$(git -C "$NSORAN" status --porcelain -- src scratch | wc -l)

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

run_one() {  # mode ues seed
    local mode=$1 ues=$2 seed=$3
    local dir="$OUT/$mode/ues$ues/seed$(printf %02d "$seed")"
    rm -rf "$dir"; mkdir -p "$dir"; : > "$dir/ts_actions_for_ns3.csv"
    local args="--configuration=0 --ues=$ues --trafficModel=3 --handoverMode=$mode \
--hoSinrDifference=3 --outageThreshold=-5.0 --minSpeed=2 --maxSpeed=4 \
--indicationPeriodicity=0.1 --enableE2FileLogging=1 --enableTraces=1 \
--simTime=$SIMTIME --RngRun=$seed"
    printf 'commit %s (dirty src/scratch files: %s)\n%s %s\n' "$COMMIT" "$DIRTY" "$BIN" "$args" > "$dir/cmd.txt"
    log "START $mode ues$ues seed$seed"
    ( cd "$dir" && /usr/bin/time -f "%e %M" -o time.txt "$BIN" $args > run.log 2>&1 )
    local ec=$?
    if [ $ec -eq 0 ]; then
        touch "$dir/DONE"; log "DONE  $mode ues$ues seed$seed ($(cat "$dir/time.txt"))"
    else
        log "FAIL  $mode ues$ues seed$seed exit=$ec"
    fi
}

log "=== sweep start: commit $COMMIT, maxpar $MAXPAR, simTime $SIMTIME"
total=0; skipped=0
for ues in $UES_LIST; do
    for seed in $SEEDS; do
        for mode in $MODES; do
            total=$((total + 1))
            if [ -f "$OUT/$mode/ues$ues/seed$(printf %02d "$seed")/DONE" ]; then
                skipped=$((skipped + 1)); continue
            fi
            while [ "$(jobs -rp | wc -l)" -ge "$MAXPAR" ] || \
                  [ "$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)" -lt "$MIN_FREE_MB" ]; do
                sleep 20
            done
            run_one "$mode" "$ues" "$seed" &
            sleep 2
        done
    done
done
wait
log "=== sweep end: total $total, skipped(already done) $skipped, done now $(find "$OUT" -name DONE | wc -l), failed $(grep -c '^.* FAIL ' "$LOG")"
