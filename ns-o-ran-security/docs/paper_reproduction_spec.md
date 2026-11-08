# TMC 2024 paper reproduction spec (paper vs code)

Paper: A. Lacava et al., "Programmable and Customized Intelligence for Traffic Steering in
5G Networks Using Open RAN Architectures", IEEE TMC 2024 (arXiv 2209.14171).
Extracted 2026-11-05 from the arXiv PDF, Section 4.2 and 5.1, Table 1, Figs. 5-9.

## 1. Availability

| Part | Public? | Notes |
|---|---|---|
| ns-3 scenario (ns-O-RAN) | yes | footnote 1 points only to `sim/ns3-o-ran-e2` (E2 module) |
| Baselines RAN RRM / SON1 / SON2 | yes | built into ns-3 `LteEnbRrc` (see 3) |
| Trained RL agent (REM + CQL CNN) | **no** | no weights, no TS xApp code, no dataset (40M points, >2000 sims) |
| TS xApp + RIC ETL/data repository | **no** | paper describes it; not in the RIC sample xApp |

So "RIC RL" has to be **re-trained** from data we generate, following Table 1.
Baselines can be reproduced exactly with ns-3 alone (no RIC needed).

## 2. Scenario (Sec. 5.1, Fig. 5) vs code

| Item | Paper | `master` scenario-one.cc (used, pinned `8c42089d`) | `v1.0` scenario-one.cc (old) |
|---|---|---|---|
| Nodes | 1 eNB + 7 gNB (one co-located at center, hex grid) | 1 + 7 | **1 + 4** |
| Configs | 850 MHz / ISD **1700 m**; 3.5 GHz / ISD 1000 m | 850 MHz ISD **1000**; 3.5 GHz ISD 1000; 28 GHz ISD 200 (`configuration` 0/1/2) | 3.5 GHz ISD 1000 hard-coded |
| BW | gNB 20 MHz, eNB 10 MHz | gNB 20 MHz | gNB 20 MHz |
| Channel | text: 3GPP UMa; Fig. 5: UMi Street Canyon | UMi Street Canyon | — |
| Numerology | 2 | check | check |
| UEs | 42, 63, 84, 105, 126 total (= 6/9/12/15/18 per gNB) | `ues` per gNB, default 7 | 3 per gNB hard-coded |
| Mobility | random walk, 2.0-4.0 m/s | `minSpeed`/`maxSpeed` 2/4 | fixed |
| Traffic | 25% each: full buffer (MBR 20 Mbit/s), bursty 3 Mbit/s, 750 kbit/s, 150 kbit/s | `trafficModel=3` (same mix) | none |
| E2 period | 100 ms | `indicationPeriodicity` 0.1 | 0.1 |
| Sim duration / runs | not stated ("multiple independent runs") | `simTime`, `--RngRun` | |

Paper-internal inconsistencies (UMa vs UMi, ISD 1700 vs code 1000) must be fixed by a
documented choice. Recommended: follow the paper text for ISD (1700 m at 850 MHz), keep UMi
as in Fig. 5 and the released code, and record the choice.

## 3. Baselines (Sec. 5.1) — exact ns-3 mapping

| Paper name | Rule | ns-3 `LteEnbRrc::SecondaryCellHandoverMode` |
|---|---|---|
| RAN RRM | HO if target SINR > serving + 3 dB | `Threshold` (`HoSinrDifference`=3) |
| SON1 | threshold 3 dB + fixed TTT 110 ms | `FixedTtt` (`FixedTttValue`=110 ms, default) |
| SON2 | threshold + dynamic TTT | `DynamicTtt` (`MinDynTttValue` 25, `MaxDynTttValue` 150 ms, defaults) |
| RIC RL | xApp decides; built-in HO disabled | `NoAuto` + control (E2 RC or `ts_actions_for_ns3.csv`) |

Verified: defaults in `master` `src/lte/model/lte-enb-rrc.cc` match the paper values.

## 4. RL agent (Sec. 4.2, Table 1)

- State per UE: for serving + neighbour cells (up to 7): SINR_u,c (CU-CP L3 RRC),
  PRB_c, Z_c (active UEs), P_c (TBs), p_QPSK, p_16QAM, p_64QAM (DU), + cell id
  → 8 params/cell, plus (t - t'_u) concatenated after flatten.
  Missing values: look back a small window ϵ (tens to hundreds of ms).
  (**This look-back is itself a temporal-misalignment mechanism in the original design.**)
- Action: {HO(c1..c7), no-HO}; network outputs N=7 actions.
- Reward: β_u (log R_{t+1} - log R_t) - K0 e^{-δ(t - t'_u)} x, with K0=1, δ=0.1;
  R from CU-UP KPM.
- Algorithm: offline DQN with REM (200 heads) + CQL regularizer.
- Net: Conv1D(32 filters, kernel 8, stride 8, ReLU) → Flatten(225) ⊕ (t-t'_u) →
  Dense 128 → Dense 32 → Dense 1400 (=200×7).
- Training: Adam lr 5e-5, batch 32, gamma 0.99, target update 8000, min replay 20000,
  replay capacity 1e6, 400 iterations × 100k steps, episode length 1.
- Data: >2000 sims under the 3 baselines (behaviour policy µ).

## 5. Metrics / headline results to compare against

- Avg UE PDCP throughput (LTE+NR), 10th/95th percentile, SINR CDF (126 UEs),
  per-UE and per-cell spectral efficiency, DL PRB %, mobility overhead H_u.
- 850 MHz (Figs. 7-8): RIC RL ≈ +50% avg throughput, +30% p10, ≈+60% p95,
  +52% UE SE, +35% cell SE vs baselines; H_u similar to baselines (higher at 42 UEs).
- Fig. 9: ratio RIC RL / SON2 for 850 MHz and C-band.
  Exact curve values are only in the figures (read off plots if needed).
