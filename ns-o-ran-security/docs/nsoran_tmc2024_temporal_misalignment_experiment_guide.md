# ns-O-RAN Traffic Steering Baseline Reproduction & Temporal-Misalignment Experiment Guide

> Target backbone  
> **A. Lacava et al., “Programmable and Customized Intelligence for Traffic Steering in 5G Networks Using Open RAN Architectures,” IEEE Transactions on Mobile Computing, 2024.**
>
> Main objective  
> 1. Reproduce the `scenario-one` traffic-steering environment.  
> 2. Verify the `E2 KPM -> xApp -> E2/RC control -> handover/traffic steering` closed loop.  
> 3. Freeze a clean aligned baseline.  
> 4. Add KPM history buffering and temporal-misalignment logic **inside the authorized xApp**.  
> 5. Compare aligned vs. misaligned decision states under the same topology, traffic, model, and permissions.

---

# 0. Important repository/version note

The current public ns-O-RAN repository has evolved since the TMC paper.

Repository:

```bash
https://github.com/wineslab/ns-o-ran-ns3-mmwave
```

There are two useful starting points.

## Option A — Recommended first: reproduce the original Traffic Steering baseline

Use the **`v1.0` release/tag** first.

The project release notes state that `v1.0` is the official legacy release that supports the Traffic Steering use case in online/bridged mode and the older `waf` workflow.

This is the safest choice when the first goal is:

```text
"Can I reproduce the TMC Traffic Steering pipeline?"
```

Clone:

```bash
git clone https://github.com/wineslab/ns-o-ran-ns3-mmwave.git
cd ns-o-ran-ns3-mmwave

git checkout v1.0
git status
```

Create your own research branch immediately:

```bash
git checkout -b temporal-misalignment-baseline
```

## Option B — Later: current CMake/Gymnasium-oriented version

The newer ns-O-RAN release moved to the CMake/ns-3 launcher workflow and added semaphore-based interaction for external controllers/Gymnasium.

This may become more convenient when implementing repeated attacks and RL experiments.

Do **not** migrate to this version before obtaining one clean baseline result from Option A.

Recommended order:

```text
v1.0 baseline reproduction
        ↓
freeze baseline commit/results
        ↓
implement attack
        ↓
only then evaluate whether current master/3.38 is worth migrating to
```

---

# 1. Target architecture

The experiment should ultimately look like:

```text
                  ┌────────────────────────────┐
                  │       Near-RT RIC          │
                  │                            │
                  │   ┌────────────────────┐   │
E2 KPM ---------->│   │ Traffic Steering   │   │
                  │   │       xApp         │   │
                  │   │                    │   │
                  │   │ KPM history buffer │   │
                  │   │        ↓           │   │
                  │   │ state constructor  │   │
                  │   │        ↓           │   │
                  │   │ decision model     │   │
                  │   └─────────┬──────────┘   │
                  └─────────────┼──────────────┘
                                │
                         control action
                                │
                                v
                      ns-O-RAN / ns-3 RAN
```

For the security experiment:

```text
Aligned
-------
K_t -> A_aligned -> N -> a_t


Misaligned
----------
{K_t, K_t-1, ..., K_t-H}
        ↓
    A_misaligned
        ↓
e.g. [RSRP_t, SINR_t-2, PRB_t-5]
        ↓
        N
        ↓
       a'_t
```

The decision model `N`, permissions, topology, traffic, and control interface must remain unchanged between the two conditions.

---

# 2. Host environment

The OpenRAN Gym installation tutorial was originally documented around **Ubuntu 20.04 LTS**.

If possible, use:

```text
Ubuntu 20.04 LTS or a compatible clean VM
Docker
Git
CMake
gcc/g++
Python 3
SCTP development libraries
```

For reproducibility, using a dedicated Ubuntu VM is preferable to modifying an existing research workstation.

Example dependencies:

```bash
sudo apt-get update

sudo apt-get install -y \
    build-essential \
    git \
    cmake \
    libsctp-dev \
    autoconf \
    automake \
    libtool \
    bison \
    flex \
    libboost-all-dev \
    g++ \
    python3 \
    python3-pip
```

Check:

```bash
gcc --version
g++ --version
cmake --version
python3 --version
git --version
docker --version
```

Create a workspace:

```bash
mkdir -p ~/research/nsoran
cd ~/research/nsoran
```

---

# 3. Install the Near-RT RIC

The OpenRAN Gym tutorial uses the WiNES Lab / Colosseum Near-RT RIC.

Clone:

```bash
cd ~/research/nsoran

git clone -b ns-o-ran \
    https://github.com/wineslab/colosseum-near-rt-ric.git

cd colosseum-near-rt-ric/setup-scripts
```

Import/build/start the RIC:

```bash
./import-wines-images.sh
./setup-ric-bronze.sh
```

Verify containers:

```bash
docker ps
```

At minimum, verify that the E2 termination is running.

Monitor E2Term logs:

```bash
docker logs e2term -f --since=1s 2>&1
```

A more focused view used in the tutorial is:

```bash
docker logs e2term -f --since=1s 2>&1 | grep gnb:
```

Record the E2Term IP:

```bash
docker inspect -f \
'{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
e2term
```

Save this value.

Example:

```text
E2TERM_IP=10.x.x.x
```

Do not blindly use an IP copied from an online example.

---

# 4. Start the example xApp environment

Open another terminal:

```bash
cd ~/research/nsoran/colosseum-near-rt-ric/setup-scripts

./start-xapp-ns-o-ran.sh
```

The script should place you inside the xApp container.

Inside:

```bash
cd /home/sample-xapp
./run_xapp.sh
```

At this point keep three terminals available:

```text
Terminal A: E2Term logs
Terminal B: xApp logs
Terminal C: ns-O-RAN simulator
```

Do not proceed to the attack implementation yet.

First confirm plain E2 connectivity.

---

# 5. Install E2Sim

Back on the host:

```bash
cd ~/research/nsoran

git clone \
    https://github.com/wineslab/ns-o-ran-e2-sim.git \
    oran-e2sim

cd oran-e2sim/e2sim
```

Build with debug logging:

```bash
mkdir -p build

./build_e2sim.sh 3
```

`3` enables verbose/debug E2 message logging.

After installation:

```bash
sudo ldconfig
```

If this step fails, fix it before touching ns-3.

---

# 6. Clone ns-O-RAN

For paper-oriented reproduction:

```bash
cd ~/research/nsoran

git clone \
    https://github.com/wineslab/ns-o-ran-ns3-mmwave.git

cd ns-o-ran-ns3-mmwave

git checkout v1.0
git checkout -b temporal-misalignment-baseline
```

Verify:

```bash
git log -1 --oneline
git status
```

Save the exact commit:

```bash
git rev-parse HEAD
```

Put it in:

```text
experiment_metadata.txt
```

Example:

```bash
echo "ns-o-ran commit: $(git rev-parse HEAD)" \
    > experiment_metadata.txt
```

---

# 7. Add the ns-O-RAN E2 interface module if required

The OpenRAN Gym setup instructions install the O-RAN SC ns-3 E2 interface in `contrib`.

Check first:

```bash
ls contrib
```

If `oran-interface` is absent:

```bash
cd contrib

git clone -b master \
    https://github.com/o-ran-sc/sim-ns3-o-ran-e2.git \
    oran-interface

cd ..
```

Do not create a second copy if the checked-out release already contains/links the required interface.

---

# 8. Build ns-O-RAN

Because the repository changed build systems over time, check which launcher exists:

```bash
ls -l waf ns3 2>/dev/null
```

## For the `v1.0`/legacy workflow

If `waf` exists:

```bash
./waf configure --enable-examples --enable-tests
./waf build
```

If the checked-out tree uses the ns-3 launcher wrapper instead:

```bash
./ns3 configure --enable-examples --enable-tests
./ns3 build
```

Do not mix build directories between branches.

If changing branch/release, preferably clean the build tree first.

---

# 9. First smoke test: Scenario Zero

Before `scenario-one`, verify the RIC connection using `scenario-zero`.

Use the command corresponding to the checked-out build system.

Example:

```bash
./ns3 run scratch/scenario-zero.cc
```

or legacy:

```bash
./waf --run "scratch/scenario-zero"
```

Expected logical sequence:

```text
1. E2 Setup Request
2. E2 Setup Response
3. E2 Subscription Request
4. E2 Subscription Response
5. E2SM RIC Indication messages
```

Check all three terminals.

### PASS criterion

You should see:

```text
ns-3 E2 node <----> E2Term <----> xApp
```

with periodic indication messages.

### Do not proceed if

```text
E2 setup fails
subscription fails
no indication reaches xApp
E2Term IP is incorrect
SCTP connection repeatedly resets
```

---

# 10. Locate and inspect Scenario One

The Traffic Steering implementation is associated with:

```text
scratch/scenario-one.cc
```

Check:

```bash
find . -name "scenario-one*"
```

Then inspect its options:

```bash
grep -n "AddValue" scratch/scenario-one.cc
```

Also inspect:

```bash
grep -n \
    -e "handover" \
    -e "control" \
    -e "E2" \
    -e "KPM" \
    -e "indication" \
    scratch/scenario-one.cc
```

The current repository's `run-simulations.sh` documents useful Traffic Steering parameters such as:

```text
handoverMode = NoAuto
indicationPeriodicity
control action file/path
number of UEs
UE speed
traffic model
carrier configuration
E2 reporting enable/disable
```

Before changing anything, create:

```text
docs/baseline_scenario_parameters.md
```

and record every value.

---

# 11. Run Scenario One without your attack

The repository includes a helper script:

```bash
./run-simulations.sh
```

Before running it, inspect it:

```bash
less run-simulations.sh
```

Important Traffic Steering settings seen in the current implementation include the conceptual configuration:

```text
use_case = Traffic Steering
handoverMode = NoAuto
indicationPeriodicity ≈ 0.1 s
control path = Traffic Steering action file
```

Do not assume these are identical across tags/releases.

Use the values from **your checked-out source**.

Also replace:

```text
e2TermIp
```

with the actual E2Term address.

Run a very short test first:

```text
simTime = 1–10 s
UE count = small
one random seed
```

Only after the pipeline works should you increase simulation duration.

---

# 12. Verify Traffic Steering control separately from AI

Before inserting the original or reconstructed AI model, verify that the control plane itself works.

Goal:

```text
known KPM
    ↓
manually selected serving cell
    ↓
control action
    ↓
UE moves/changes serving cell
```

Create a deterministic test:

```text
UE 0:
    current cell = Cell A

manual action:
    target = Cell B
```

Verify from logs/traces that the control action actually changes the serving relationship.

This is important because otherwise:

```text
"attack had no effect"
```

could simply mean:

```text
"control path was broken"
```

---

# 13. Verify KPM collection

Before using any NN/RL model, dump the raw KPM stream.

For every indication store at least:

```text
simulation_time
arrival_time if available
UE identifier
cell identifier
KPM / feature name
measurement value
measurement/reporting sequence identifier if available
```

Recommended local representation:

```python
Measurement = {
    "sim_time": ...,
    "ue_id": ...,
    "cell_id": ...,
    "feature": ...,
    "value": ...,
}
```

Initially write all observations to a CSV.

Example target:

```text
logs/kpm_raw_seed001.csv
```

Possible columns:

```text
sim_time,
ue_id,
serving_cell,
candidate_cell,
rsrp,
rsrq,
sinr,
prb_usage,
throughput,
...
```

The exact KPM set must follow what `scenario-one` actually exposes.

Do **not** invent missing KPMs just to match the planned paper.

---

# 14. Freeze the clean baseline

Once Scenario One runs correctly:

```bash
git add .
git commit -m "Baseline: reproducible ns-O-RAN scenario-one traffic steering"
```

Tag it:

```bash
git tag baseline-aligned-v1
```

Save:

```text
commit hash
OS version
Docker version
ns-O-RAN version
E2Sim version
RIC version
xApp version
scenario parameters
random seeds
```

This becomes the reference environment for every security experiment.

---

# 15. AI victim model: important reproducibility point

Do not assume that cloning `ns-o-ran-ns3-mmwave` automatically gives the complete trained Traffic Steering policy from the TMC paper.

Treat the project as two separable parts:

```text
Part A
------
ns-O-RAN scenario
E2 telemetry
control loop
traffic steering environment


Part B
------
decision model / victim xApp
```

First reproduce **Part A completely**.

Then determine exactly which public code/model artifacts are available for Part B.

Search locally:

```bash
find . \
    \( -iname "*.pt" \
    -o -iname "*.pth" \
    -o -iname "*.onnx" \
    -o -iname "*.h5" \
    -o -iname "*.pkl" \
    -o -iname "*dqn*" \
    -o -iname "*cql*" \
    -o -iname "*traffic*steer*" \)
```

Also clone/inspect the xApp repos linked by ns-O-RAN:

```bash
cd ~/research/nsoran

git clone \
    https://github.com/wineslab/ns-o-ran-scp-ric-app-kpimon.git

git clone \
    https://github.com/wineslab/ns-o-ran-xapp-rc.git
```

Do **not** start the security experiment until you know precisely:

```text
what model receives the state
what state vector it receives
what action space it outputs
where the state is assembled
where the control action is emitted
```

---

# 16. Code points to locate before attack implementation

Find the following five points.

## P1. KPM reception callback

Locate where an E2 Indication enters the xApp.

Conceptually:

```python
def on_kpm_indication(msg):
    ...
```

## P2. KPM decoding

Locate:

```text
E2 message
    ↓
RSRP / RSRQ / SINR / PRB / ...
```

## P3. State construction

This is the most important point.

Locate the exact code equivalent of:

```python
state = [
    feature_1,
    feature_2,
    ...
]
```

Call this function:

```text
A : KPM history -> decision state
```

even if the original code does not use that name.

## P4. Model inference

Locate:

```python
action = model(state)
```

Call this:

```text
N : state -> action
```

## P5. Control transmission

Locate where:

```text
action -> target cell -> E2/RC control
```

is encoded/sent.

---

# 17. Refactor before adding the attack

Do **not** insert arbitrary `if attack:` statements everywhere.

First refactor to:

```python
history = update_history(kpm)

state = build_state(
    history=history,
    mode="aligned",
)

action = policy(state)

send_control(action)
```

Target structure:

```text
receive_kpm()
      ↓
update_history()
      ↓
build_state()       <-- attack surface A
      ↓
policy()            <-- victim decision logic N
      ↓
send_control()
```

This separation is essential for the paper.

---

# 18. Add the KPM history buffer

For each UE, maintain a bounded history.

Conceptually:

```python
from collections import deque

history = {
    ue_id: deque(maxlen=H)
}
```

Each entry should include a timestamp.

Example:

```python
snapshot = {
    "time": t,
    "ue_id": ue_id,
    "rsrp": rsrp,
    "rsrq": rsrq,
    "sinr": sinr,
    "prb": prb,
    "throughput": throughput,
}
```

Insert:

```python
history[ue_id].append(snapshot)
```

Never overwrite the original measurement timestamp.

---

# 19. Experiment mode 0 — Aligned baseline

Define:

```python
def build_state_aligned(history):
    return history[-1]
```

or feature-wise:

```text
RSRP <- K_t
RSRQ <- K_t
SINR <- K_t
PRB  <- K_t
...
```

Formally:

```text
z_t = A_aligned(W_t)
```

This must reproduce the baseline policy as closely as possible.

---

# 20. Experiment mode 1 — Uniform stale state

First attack:

```text
all features come from K_(t-k)
```

Example:

```python
def build_state_uniform_lag(history, k):
    return history[-1-k]
```

Formally:

```text
z'_t = K_(t-k)
```

Test:

```text
k = 1
k = 2
k = 3
k = 5
...
```

This is the simplest sanity-check attack.

---

# 21. Experiment mode 2 — Feature-wise temporal misalignment

This should become the main attack.

Example:

```text
RSRP <- K_t
RSRQ <- K_t
SINR <- K_(t-2)
PRB  <- K_(t-5)
```

Pseudo-code:

```python
def build_state_feature_lag(history, lag):
    return {
        "rsrp": history[-1-lag["rsrp"]]["rsrp"],
        "rsrq": history[-1-lag["rsrq"]]["rsrq"],
        "sinr": history[-1-lag["sinr"]]["sinr"],
        "prb":  history[-1-lag["prb"]]["prb"],
    }
```

Formally:

```text
z'_t = [
    K_RSRP(t-k1),
    K_RSRQ(t-k2),
    K_SINR(t-k3),
    K_PRB(t-k4)
]
```

where:

```text
not all k_i are equal
```

This cleanly separates the work from a plain delay/staleness study.

---

# 22. Experiment mode 3 — Critical-time selective attack

Do not attack every timestep.

Define:

```text
g_t = criticality score
```

Attack only if:

```text
g_t >= threshold
```

Possible criticality indicators:

```text
Top-1 vs Top-2 action-value margin
HO decision boundary proximity
serving/candidate SINR difference
rapid RSRP trend
cell load crossover
policy confidence / entropy
```

Conceptually:

```python
if is_critical(current_context):
    state = build_state_misaligned(history)
else:
    state = build_state_aligned(history)
```

This supports the paper's stealthy/selective attack framing.

---

# 23. Mandatory provenance logging

For every decision, log **which measurement epoch generated each feature**.

Example:

```text
decision_id = 381
consume_time = 12.300

RSRP:
    source_time = 12.300
    lag = 0

SINR:
    source_time = 12.100
    lag = 0.200

PRB:
    source_time = 11.800
    lag = 0.500

selected_action:
    target_cell = 3
```

Recommended CSV:

```text
logs/decision_provenance.csv
```

Columns:

```text
seed,
decision_id,
ue_id,
consume_time,
rsrp_time,
rsrq_time,
sinr_time,
prb_time,
rsrp_age,
rsrq_age,
sinr_age,
prb_age,
max_temporal_skew,
selected_action,
serving_cell,
attack_mode
```

Compute:

```text
Age_i = t_consume - t_i

TemporalSkew =
    max_i(t_i) - min_i(t_i)
```

This log is critical evidence for the paper.

---

# 24. Attack conditions to implement first

Minimum experiment matrix:

| ID | State construction | Purpose |
|---|---|---|
| B0 | aligned | clean baseline |
| B1 | uniformly stale | staleness control |
| A1 | one feature stale | sensitivity |
| A2 | two features independently stale | temporal misalignment |
| A3 | random feature-wise lag | generic attack |
| A4 | critical-time selective lag | main security attack |

Do not start with a complex optimizer.

First prove:

```text
A2/A4 > meaningful degradation relative to B0
```

while:

```text
all KPM values remain genuine
all E2 permissions remain unchanged
all control messages remain valid
```

---

# 25. Suggested lag units

Prefer expressing lag in both:

```text
number of reports k
```

and:

```text
actual time Δt
```

Example, if reporting interval is `100 ms`:

```text
k = 1 -> 100 ms
k = 2 -> 200 ms
k = 5 -> 500 ms
k = 10 -> 1 s
```

Store both in results.

The paper should not report only `k`, because reviewers will ask whether the result depends on the reporting periodicity.

---

# 26. Metrics

At minimum collect:

## Network performance

```text
per-UE throughput
per-cell throughput
PRB utilization
latency if exposed
packet loss / delivery ratio if exposed
```

## Mobility

```text
handover count
handover rate
handover success/failure
RLF if exposed
ping-pong HO
time attached to sub-optimal cell
```

## Decision quality

```text
action disagreement:
    a_aligned != a_attack

target-cell disagreement rate

cumulative utility/reward

policy confidence/Q-value margin if available
```

## Security/attack

```text
attack rate
number of manipulated decision epochs
KPM modification count = 0
average temporal skew
maximum temporal skew
performance loss per attacked epoch
```

A particularly useful metric:

```text
Attack Efficiency
=
Performance degradation
-----------------------
Number of attacked decisions
```

---

# 27. Reproducibility protocol

Use identical random seeds for paired runs.

Example:

```text
seed 1:
    aligned
    uniform stale
    feature-wise attack

seed 2:
    aligned
    uniform stale
    feature-wise attack
...
```

Recommended initial development:

```text
5 seeds
```

Final paper experiments:

```text
>= 10–20 independent seeds
```

depending on simulation cost and variance.

Keep:

```text
same topology
same UE trajectories
same traffic realization
same initial association
same policy weights
```

between paired aligned/attack runs.

---

# 28. Suggested directory structure

Create a separate experiment wrapper instead of polluting source files.

```text
ns-o-ran-security/
├── README.md
├── configs/
│   ├── baseline.yaml
│   ├── uniform_lag.yaml
│   ├── feature_lag.yaml
│   └── selective_attack.yaml
│
├── xapp/
│   ├── kpm_buffer.py
│   ├── state_builder.py
│   ├── policy_wrapper.py
│   ├── attack_policy.py
│   └── provenance_logger.py
│
├── scripts/
│   ├── run_baseline.sh
│   ├── run_attack.sh
│   ├── run_all_seeds.sh
│   └── collect_results.py
│
├── logs/
│
├── results/
│   ├── raw/
│   └── processed/
│
└── notebooks/
    └── analysis.ipynb
```

---

# 29. First-week execution plan

## Day 1 — Environment only

Goal:

```text
RIC up
E2Term up
xApp container up
ns-O-RAN builds
```

No ML.

## Day 2 — E2 connectivity

Goal:

```text
Scenario Zero
E2 Setup
Subscription
KPM Indication
```

Save screenshots/logs.

## Day 3 — Scenario One

Goal:

```text
Scenario One starts
KPM generated
Traffic Steering control path identified
```

## Day 4 — Manual control

Goal:

```text
manual target-cell action
actual serving-cell change
```

## Day 5 — State extraction

Goal:

```text
exact model input vector identified
timestamped KPM logger completed
```

## Day 6 — Aligned victim

Goal:

```text
policy(state_t) -> action
```

with clean baseline.

## Day 7 — First attack

Implement only:

```text
uniform lag k=1,2,5
```

If this works, move to feature-wise misalignment.

---

# 30. Minimal success milestone before doing serious experiments

Do not run large experiments until the following test passes.

For one UE:

```text
t = 10.0
KPM_t received

t = 10.1
KPM_t+1 received

t = 10.2
KPM_t+2 received
```

Aligned log:

```text
decision @ 10.2
RSRP <- 10.2
SINR <- 10.2
PRB  <- 10.2
```

Attack log:

```text
decision @ 10.2
RSRP <- 10.2
SINR <- 10.1
PRB  <- 10.0
```

Both must produce:

```text
valid policy input
valid xApp execution
valid control message
```

with no change to:

```text
authentication
authorization
E2 subscription
control privilege
KPM values
```

If this works, the core reachability assumption of the paper has been experimentally demonstrated.

---

# 31. Defense implementation comes later

Do not implement PE/temporal encoding or the trusted temporal monitor yet.

First establish the vulnerability.

Recommended paper sequence:

```text
Phase 1
-------
Aligned baseline


Phase 2
-------
Temporal-misalignment attack


Phase 3
-------
Attack characterization


Phase 4
-------
Defense:
temporal contract / trusted state construction


Phase 5
-------
Optional:
measurement-age encoding / temporal-aware model
```

Otherwise it becomes difficult to separate:

```text
attack contribution
```

from:

```text
defense contribution
```

---

# 32. Suggested defense experiment after the attack is stable

Later introduce:

```text
Trusted Temporal State Constructor
```

that checks:

```text
Age_i <= tau_i
```

and:

```text
max(t_i) - min(t_i) <= epsilon
```

before generating the model state.

Optional second layer:

```text
value embedding
+
feature-type embedding
+
measurement-age encoding
```

for temporal-aware inference.

Security validation and model robustness should be evaluated separately.

---

# 33. Git workflow

Do not develop directly on the baseline branch.

Recommended:

```bash
# clean reproduction
git checkout temporal-misalignment-baseline

# attack implementation
git checkout -b attack-state-builder

# later
git checkout temporal-misalignment-baseline
git checkout -b defense-temporal-contract
```

Tags:

```bash
git tag baseline-aligned-v1
git tag attack-uniform-lag-v1
git tag attack-feature-lag-v1
git tag defense-temporal-contract-v1
```

---

# 34. What to record for the paper

Keep a machine-readable experiment manifest.

Example:

```yaml
experiment_id: seed001_feature_lag
seed: 1

nsoran:
  commit: "<git hash>"
  scenario: "scenario-one"

e2:
  indication_period_ms: 100

ue:
  count: 42
  min_speed_mps: ...
  max_speed_mps: ...

attack:
  enabled: true
  type: "feature-wise-temporal-misalignment"

  lag:
    rsrp: 0
    rsrq: 0
    sinr: 2
    prb: 5

policy:
  checkpoint: "..."
  hash: "..."

output:
  provenance_log: "..."
  metrics_log: "..."
```

This will save substantial time when writing the evaluation section.

---

# 35. Immediate checklist

Run these in order.

```text
[ ] 1. Create clean Ubuntu environment
[ ] 2. Install Docker/dependencies
[ ] 3. Clone Colosseum Near-RT RIC
[ ] 4. Start E2Term
[ ] 5. Start sample xApp
[ ] 6. Install ns-O-RAN E2Sim
[ ] 7. Clone ns-o-ran-ns3-mmwave
[ ] 8. Checkout v1.0 for first paper-oriented reproduction
[ ] 9. Build
[ ] 10. Run Scenario Zero
[ ] 11. Confirm E2 Setup/Subscription/Indication
[ ] 12. Run Scenario One
[ ] 13. Log raw KPMs
[ ] 14. Verify manual traffic-steering action
[ ] 15. Identify exact state-construction code
[ ] 16. Identify exact inference code
[ ] 17. Identify exact control-send code
[ ] 18. Freeze aligned baseline
[ ] 19. Add per-UE KPM history
[ ] 20. Add provenance logging
[ ] 21. Test uniform lag
[ ] 22. Test feature-wise misalignment
[ ] 23. Add critical-time selective attack
[ ] 24. Only then build the defense
```

---

# 36. Primary references / code

## Main ns-O-RAN repository

```text
https://github.com/wineslab/ns-o-ran-ns3-mmwave
```

The repository explicitly identifies `scenario-one.cc` / Traffic Steering as associated with the Lacava et al. TMC work.

## ns-O-RAN releases

```text
https://github.com/wineslab/ns-o-ran-ns3-mmwave/releases
```

Useful distinction:

```text
v1.0
    legacy Traffic Steering online/bridged implementation

newer 3.38/master
    CMake pipeline
    semaphore/external-controller support
    Gymnasium-oriented development
```

## OpenRAN Gym ns-O-RAN setup tutorial

```text
https://openrangym.com/tutorials/ns-o-ran
```

Covers:

```text
Colosseum Near-RT RIC
E2Term
sample xApp
E2Sim
ns-O-RAN
Scenario Zero
E2 setup/subscription/indication verification
```

## Near-RT RIC

```text
https://github.com/wineslab/colosseum-near-rt-ric
```

## E2Sim

```text
https://github.com/wineslab/ns-o-ran-e2-sim
```

## KPM monitoring xApp

```text
https://github.com/wineslab/ns-o-ran-scp-ric-app-kpimon
```

## RC xApp

```text
https://github.com/wineslab/ns-o-ran-xapp-rc
```

## Gymnasium wrapper

```text
https://github.com/wineslab/ns-o-ran-gym-environment
```

---

# 37. Recommended first stopping point

Before implementing any sophisticated attack algorithm, stop when you can produce this single table from your own logs:

| Decision | RSRP epoch | SINR epoch | PRB epoch | Action | Valid E2 control? |
|---|---:|---:|---:|---|---|
| aligned | t | t | t | Cell 2 | Yes |
| misaligned | t | t-2 | t-5 | Cell 3 | Yes |

If you can demonstrate this while the KPM values themselves are unchanged and the same authorized xApp/control path is used, the experimental foundation for the paper is in place.

---

# 38. Final recommended workflow

```text
STEP 1
Reproduce ns-O-RAN + RIC connectivity

        ↓

STEP 2
Reproduce scenario-one Traffic Steering

        ↓

STEP 3
Identify exact KPM -> state -> policy -> control path

        ↓

STEP 4
Freeze aligned baseline

        ↓

STEP 5
Add timestamped per-UE history buffer

        ↓

STEP 6
Uniform lag sanity test

        ↓

STEP 7
Feature-wise temporal misalignment

        ↓

STEP 8
Selective/critical-time attack

        ↓

STEP 9
Evaluate network + mobility + attack-efficiency metrics

        ↓

STEP 10
Implement temporal-contract defense

        ↓

STEP 11
Optional temporal/measurement-age encoding
```

The key principle is:

```text
Do not modify the RAN values.

Do not modify authorization.

Do not change the victim model between aligned and attack runs.

Only change which genuine measurement epoch is used to construct the xApp decision state.
```

That is the cleanest experimental realization of the proposed security problem.
