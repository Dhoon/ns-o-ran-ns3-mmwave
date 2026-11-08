# Baseline Scenario Parameters (guide section 10)

Recorded from the checked-out source **before** any modification.

- Repo: `wineslab/ns-o-ran-ns3-mmwave`
- Tag: `v1.0`
- Commit: `0efbfaf370350c170beb249951e5c349d7f89b34`
- Branch: `temporal-misalignment-baseline`
- Build system present: `waf` (legacy workflow; no `ns3` launcher in this tag)
- Scenario: `scratch/scenario-one.cc`
- E2 interface: `contrib/oran-interface` @ `cf1a4bc` (o-ran-sc/sim-ns3-o-ran-e2, master)

## scenario-one global values (grep "AddValue" / GlobalValue)

`AddValue` is not used directly; parameters are declared as `GlobalValue`
objects and read via `GlobalValue::GetValueByName`. Traffic-steering-relevant
globals observed in `scratch/scenario-one.cc`:

| Global | Role | Config target |
|---|---|---|
| `indicationPeriodicity` | E2 KPM report interval | `LteEnbNetDevice::E2Periodicity` |
| `handoverMode` | HO policy | `LteEnbRrc::SecondaryCellHandoverMode` |
| `controlFileName` | control action file path | `LteEnbNetDevice::ControlFileName` |
| `e2TermIp` | E2Term address | (runtime) |
| `outageThreshold` | HO outage trigger | (runtime) |

## Traffic Steering use-case values (from run-simulations.sh, use_case=1)

| Parameter | Value |
|---|---|
| use_case | 1 (Traffic Steering) |
| handoverMode | `NoAuto` |
| outageThreshold | `-1000` |
| indicationPeriodicity | `0.1` s (100 ms) |
| controlPath | `ts_actions_for_ns3.csv` |
| trafficModel | 3 (mixed) |
| configuration | 0 (NR 850 MHz, low traffic) |
| ues | 3 (per mmWave eNB) |
| minSpeed / maxSpeed | 2.0 / 4.0 m/s |
| e2lteEnabled / e2nrEnabled | 1 / 1 |
| e2du / e2cuUp / e2cuCp | 1 / 1 / 1 |
| enableTraces | 1 |
| EnableE2FileLogging | 1 |
| simTime | 1.0 s (raise after pipeline verified) |
| N (runs) | 1 |

> NOTE: `e2TermIp` in the stock script is `10.102.157.65` — a placeholder.
> Replace with the actual E2Term IP from `docker inspect ... e2term`
> (guide section 3). Do not reuse an online example IP.

## Status of remaining guide steps requiring a live RIC

The following still need Docker + the Colosseum Near-RT RIC running, which
is not yet installed on this host (see `../README.md` "Environment status"):

- section 3-4  start RIC / E2Term / sample xApp
- section 5    build E2Sim (`./build_e2sim.sh 3`, `sudo ldconfig`)
- section 8    `./waf configure && ./waf build`
- section 9    Scenario Zero smoke test (E2 setup/subscription/indication)
- section 11-14 run Scenario One, log raw KPMs, freeze aligned baseline
