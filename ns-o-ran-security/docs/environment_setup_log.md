# Environment Setup Log & Run Workflow

Record of what was actually built and the key findings, so the baseline is reproducible.

## Component locations

- ns-3 / ns-O-RAN sim: `~/research/nsoran/ns-o-ran-ns3-mmwave` (WSL native FS — fast build/run)
- RIC / E2Sim / xApp: `~/research/nsoran/` (WSL)
- Experiment wrapper: `ns-o-ran-security/` (inside the sim repo)
- Terminal launcher (Windows): `Desktop/ns-oran-terminals.bat` + `~/nsoran-term/{a,b,c}.sh`

## Build (done once)

- deps: build-essential cmake libsctp-dev lksctp-tools libboost-all-dev sqlite3 libsqlite3-dev pkg-config autoconf automake libtool bison flex
- `./waf configure --enable-examples --enable-tests` (SQLite stats enabled)
- `./waf build`  (~4 min on WSL native FS)
- Build-compat patches already in the source: `#include <limits>` in 30 files (GCC 11),
  `contrib/oran-interface` pinned to `h-release` (waf-compatible).

## RIC bring-up (per boot)

```bash
sudo modprobe sctp
sudo service docker start
cd ~/research/nsoran/colosseum-near-rt-ric/setup-scripts
./setup-ric-bronze.sh          # starts db, e2mgr, e2rtmansim, e2term
# xApp:
./start-xapp-ns-o-ran.sh       # then inside: cd /home/sample-xapp && ./run_xapp.sh
```
E2TERM IP: `10.0.2.10` (docker inspect e2term).

## Verified milestones

- Scenario Zero: E2 setup/subscription/indication closed loop (ns-3 <-> e2term <-> xApp). PASS.
- Scenario One (Traffic Steering): gNBs register ORAN-WG3-KPM, connect to live RIC. PASS.

## KEY FINDING: e2term crash vs reducedPmValues

- **Online scenario-one with `reducedPmValues=0` (full PM) crashes e2term** with
  `Segmentation fault (core dumped)` (exit 139) while decoding the KPM measurement
  container. ns-3 then dies with `[SCTP] Bad file descriptor`. Reproducible every run.
- **`reducedPmValues=1` avoids the crash** — online closed loop stays up.
- Reduced mode STILL delivers the traffic-steering-critical signals:
  - `HO.SrcCellQual.RS-SINR.UEID`  (serving-cell SINR, per UE)
  - `HO.TrgtCellQual.RS-SINR.UEID` (target/neighbor-cell SINR, per UE)
  - `RRU.PrbUsedDl` (cell PRB utilization)
  - `DRB.UEThpDl.UEID` (per-UE downlink throughput)
  - `DRB.MeanActiveUeDl`, top MCS-dist bins
- Reduced mode DROPS: per-UE SINR histogram bins, per-UE PRB, full MCS dist,
  buffer sizes, DRB.EstabSucc counters.
- Conclusion: **use `reducedPmValues=1` for the online baseline and attack.** The
  serving-vs-target SINR pair is kept and is the natural temporal-misalignment target.
  (If full PM is ever required online, the real fix is to patch + rebuild the e2term
  image from `colosseum-near-rt-ric/setup/e2/RIC-E2-TERMINATION`.)

## Run helpers

- `run_s1.sh [simTime]` — online scenario-one, reducedPmValues=1, e2TermIp=10.0.2.10.
- `run_s1_offline.sh [simTime] [RngRun]` — offline KPM dump (enableE2FileLogging=1, no RIC).

Note: `simTime` is simulated seconds; real wall time is ~2-4 min due to fixed ns-3
setup cost, roughly independent of simTime.
