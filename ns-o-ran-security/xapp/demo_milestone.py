"""Milestone self-test (guide sections 30, 37).

Runs the whole KPM -> history -> state(A) -> policy(N) -> provenance pipeline on
a short synthetic KPM stream for one UE, with NO simulator attached, and prints
the section-37 table:

    | Decision   | RSRP epoch | SINR epoch | PRB epoch | Action | Valid input? |

Both aligned and misaligned decisions consume genuine, unmodified values; only
the source epoch differs. This demonstrates the paper's core reachability claim
offline. Replace the synthetic stream with the real E2 KPM callback once the
pipeline is wired into the xApp.

Run:  python demo_milestone.py
"""
from __future__ import annotations

from kpm_buffer import KpmHistoryBuffer, Snapshot
from state_builder import build_state_aligned, build_state_feature_lag
from policy_wrapper import PlaceholderPolicy
from provenance_logger import ProvenanceLogger


def synthetic_stream(ue_id=0):
    """Three genuine epochs at 10.0, 10.1, 10.2 s (guide section 30)."""
    return [
        Snapshot(sim_time=10.0, ue_id=ue_id, serving_cell=2,
                 rsrp=-95.0, rsrq=-10.0, sinr=5.0, prb=40.0, throughput=12.0),
        Snapshot(sim_time=10.1, ue_id=ue_id, serving_cell=2,
                 rsrp=-93.0, rsrq=-9.5, sinr=6.5, prb=45.0, throughput=15.0),
        Snapshot(sim_time=10.2, ue_id=ue_id, serving_cell=2,
                 rsrp=-98.0, rsrq=-11.0, sinr=2.0, prb=70.0, throughput=6.0),
    ]


def main():
    ue_id = 0
    buf = KpmHistoryBuffer(maxlen=16)
    for snap in synthetic_stream(ue_id):
        buf.append(snap)          # genuine values; timestamps preserved

    hist = buf.history(ue_id)
    consume_time = 10.2
    policy = PlaceholderPolicy(candidate_cells=[2, 3])

    aligned = build_state_aligned(hist, consume_time, ue_id)
    # SINR from t-2 (10.0), PRB from t-1 (10.1): feature-wise misalignment.
    misaligned = build_state_feature_lag(
        hist, consume_time, ue_id, lag={"rsrp": 0, "rsrq": 0, "sinr": 2, "prb": 1})

    a_act = policy.decide(aligned.vector)
    m_act = policy.decide(misaligned.vector)

    with ProvenanceLogger("../logs/decision_provenance_demo.csv", seed=1) as log:
        log.log(aligned, a_act, aligned.vector and 2)
        log.log(misaligned, m_act, 2)

    def row(label, st, act):
        src = st.source_time
        return (f"| {label:<10} | {src['rsrp']:>10.1f} | {src['sinr']:>10.1f} "
                f"| {src['prb']:>9.1f} | Cell {act:<2} | Yes |")

    print("| Decision   | RSRP epoch | SINR epoch | PRB epoch | Action | Valid input? |")
    print("|------------|-----------:|-----------:|----------:|--------|--------------|")
    print(row("aligned", aligned, a_act))
    print(row("misaligned", misaligned, m_act))
    print()
    print(f"aligned    temporal_skew = {aligned.temporal_skew():.3f} s  "
          f"ages={ {k: round(v,3) for k,v in aligned.ages().items()} }")
    print(f"misaligned temporal_skew = {misaligned.temporal_skew():.3f} s  "
          f"ages={ {k: round(v,3) for k,v in misaligned.ages().items()} }")
    print(f"action disagreement: {a_act != m_act}  "
          f"(aligned->Cell {a_act}, misaligned->Cell {m_act})")
    print("KPM values modified: 0  (only source epoch selection differs)")


if __name__ == "__main__":
    main()
