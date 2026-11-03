# Next Step (start here next session)

## Where we are (done)
- Environment fully built; online closed loop works (ns-3 <-> e2term <-> xApp).
- e2term crash solved: online scenario-one must use `reducedPmValues=1`
  (full PM crashes e2term with a segfault). See `environment_setup_log.md`.
- Reduced mode keeps the traffic-steering-critical KPM:
  serving/target SINR (HO.SrcCellQual/TrgtCellQual.RS-SINR), cell PRB (RRU.PrbUsedDl),
  per-UE throughput (DRB.UEThpDl). These are the temporal-misalignment targets.
- Run with `./run_s1.sh [simTime]` (online, reduced). Desktop launcher opens the 3 terminals.
- Data feel: ns-3 trace `MmWaveSinrTime.txt` shows per-UE SINR to all candidate cells,
  swinging ~10 dB per 0.1 s. NOTE this is the ns-3 internal trace, NOT the exact E2 KPM
  the xApp receives (that is aggregated per indicationPeriodicity and, in reduced mode,
  a subset; the sample xApp does not pretty-print it).

## Next: find the Go xApp KPM -> state -> control code points (guide 16, P1-P5)
The attack goes into the authorized xApp's state construction. The running xApp is the
RIC sample xApp (Go), container `sample-xapp-24`, source under the RIC repo. Locate:
- P1 KPM reception callback (where a RIC Indication enters the xApp)
- P2 KPM decoding (E2SM-KPM -> SINR/PRB/throughput values)
- P3 state construction (features assembled for the decision) <-- attack surface A
- P4 model inference / decision (state -> target cell)
- P5 control transmission (action -> E2/RC control)

Candidate sources to read first (Go):
- RIC sample xApp: colosseum-near-rt-ric/setup/sample-xapp/ (hw_xapp_main)
  and xapp-sm-connector (the connector built into the container at /home/xapp-sm-connector)
- For reference on decode: ns-o-ran-scp-ric-app-kpimon/control/{e2sm,control}.go (kept as
  reference even though not used in the baseline)

Goal of next session: identify exactly where the received KPM becomes the decision state,
so the feature-wise temporal-misalignment (state_builder.py logic) can be wired in there.
