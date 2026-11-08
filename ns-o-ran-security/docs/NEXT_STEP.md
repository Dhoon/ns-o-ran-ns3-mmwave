# Next Step (start here next session)

## 2026-11-05: switched to paper reproduction on ns-O-RAN master
- Baseline = Lacava et al. TMC 2024. Spec: `paper_reproduction_spec.md`.
- Branch `paper-repro-master` at master `8c42089d`; oran-interface `cf1a4bc`.
  Versions, build, scenario choices: `../experiment_metadata.txt`.
- Offline smoke run (850 MHz, 6 UE/gNB, Threshold, 2 s) OK: 42 UEs, 8 cells, 103 HOs,
  0 failures. Cost 8m19s wall per 2 s sim, ~388 MB -> runtime scaling must be measured
  before planning the full sweep (3 baselines x 5 UE counts x 2 configs x seeds).
- 2026-11-09: ISD 1700 m applied (scenario-one.cc:430). ns-3 core patch: byte-tag-list.cc
  free list disabled (memory grew superlinearly under full-buffer; peak 313 -> 168 MB at
  2 s, outputs byte-identical). Details and evidence: `../experiment_metadata.txt`.
- Open: `run_s1.sh` and terminal launchers still use waf (v1.0) and are not updated.
- Section below is the v1.0-era state (online loop, P1-P5); still valid for the xApp side.

## Where we are (v1.0 era, done)
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

- P1-P5 located (2026-11-03). Full details: `xapp_code_points_P1_P5.md`.
  * The xApp is NOT Go: C++ connector (hw_xapp_main) + Python agent (run_xapp.py),
    linked by TCP 127.0.0.1:4200. It is a pure relay.
  * P1 = msgs_proc.cc:164/245 (C++) -> run_xapp.py:17 (Python). P5 = xapp.cc:347.
  * P2/P3/P4 do NOT exist: inner E2SM-KPM is forwarded still ASN.1-encoded, no state,
    no model. Attack surface A must be built (kpm_buffer/state_builder/policy_wrapper).
  * Python agent likely drops all KPM (utf-8 decode of binary -> ''); log file is 0 bytes.
  * C++ control path sends a plain string, not E2SM-RC -> ns-3 TS handover won't parse it.

## Next: choose integration path (see options A/B/C in xapp_code_points_P1_P5.md)
- A (recommended): Python xApp. Fix socket framing, decode E2SM-KPM in Python
  (asn1tools + ASN.1 from contrib/oran-interface), plug in state_builder/policy_wrapper,
  make C++ encode a proper E2SM-RC TS control (imsi, target cell).
- B (fastest first result): file loop. ns-3 ReadControlFile reads
  ts_actions_for_ns3.csv (timestamp,imsi,targetCellId) every 1 ms; KPM from ns-3 traces.
- First concrete check either way: run a sim and watch `docker logs sample-xapp-24`
  to confirm problem #1 (KPM dropped in Python).
