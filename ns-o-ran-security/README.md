# ns-O-RAN Temporal-Misalignment Security Experiment

Experiment wrapper for the study described in
`docs/nsoran_tmc2024_temporal_misalignment_experiment_guide.md`.

Backbone paper: A. Lacava et al., *"Programmable and Customized Intelligence for
Traffic Steering in 5G Networks Using Open RAN Architectures,"* IEEE TMC 2024.

## Core idea (the one invariant)

Between aligned and misaligned runs, **only the selection of which genuine KPM
measurement epoch is used to build the xApp decision state changes**. Everything
else is held fixed:

- KPM values are never altered (modification count = 0)
- victim policy `N`, topology, traffic, UE trajectories, seeds — identical
- E2 authentication / authorization / subscription / control privilege — unchanged

That is the cleanest realization of the proposed security problem (guide section 38).

## What is built here

```
ns-o-ran-security/
├── xapp/
│   ├── kpm_buffer.py        # per-UE timestamped history (guide 13, 18)
│   ├── state_builder.py     # A : history -> state; aligned + 4 attack modes (19-22)
│   ├── attack_policy.py     # mode/criticality selection B0,B1,A1-A4 (22, 24)
│   ├── policy_wrapper.py    # N : state -> action (placeholder until model located) (15-16)
│   ├── provenance_logger.py # per-decision epoch provenance CSV (23)
│   └── demo_milestone.py    # offline section-30/37 milestone self-test
├── configs/                 # baseline / uniform_lag / feature_lag / selective_attack (34)
├── scripts/                 # run_baseline.sh, run_attack.sh, run_all_seeds.sh, collect_results.py
├── docs/baseline_scenario_parameters.md   # recorded from v1.0 source (10)
├── logs/  results/  notebooks/
```

## Attack matrix (guide section 24)

| ID | State construction | Config |
|----|--------------------|--------|
| B0 | aligned | `configs/baseline.yaml` |
| B1 | uniformly stale | `configs/uniform_lag.yaml` |
| A1 | one feature stale | `feature_lag.yaml` (single non-zero lag) |
| A2 | two+ features independently stale | `configs/feature_lag.yaml` |
| A3 | random feature-wise lag | `attack_policy` mode `random` |
| A4 | critical-time selective lag | `configs/selective_attack.yaml` |

## Quick check (no simulator needed)

```bash
cd xapp && python demo_milestone.py
```

Produces the section-37 table and `logs/decision_provenance_demo.csv`,
demonstrating aligned vs. misaligned decisions from genuine epochs offline.

## Environment status

Done on this host:
- cloned ns-o-ran-ns3-mmwave @ v1.0 (`0efbfaf3`) + branch `temporal-misalignment-baseline`
- cloned RIC, E2Sim, kpimon xApp, rc xApp, oran-interface (see metadata)
- recorded baseline scenario parameters (`docs/baseline_scenario_parameters.md`)
- built + tested the xApp attack/provenance pipeline offline

Still required (needs Docker + a live Near-RT RIC, not yet installed here):
- guide 3-9  : start RIC/E2Term/xApp, build E2Sim, `./waf build`, Scenario Zero
- guide 11-15: run Scenario One, log raw KPMs, locate the victim policy `N`
- guide 16-17: find P1-P5 code points and refactor to the four-stage loop
- then bind `AttackController` into the xApp KPM callback and run the matrix

## Reproducibility

Every run carries a manifest (`configs/*.yaml`) with the ns-O-RAN commit,
scenario parameters, seed, attack lag profile, and policy hash (guide section 34).
Use paired seeds for aligned/attack runs (guide section 27).
