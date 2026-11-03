"""Mandatory decision-provenance logging (guide section 23).

For every decision we record which genuine measurement epoch produced each
feature, the per-feature age, the temporal skew, and the chosen action. This
CSV is the central evidence that KPM values were never modified: only their
source epoch varied.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from state_builder import BuiltState

COLUMNS = [
    "seed", "decision_id", "ue_id", "consume_time",
    "rsrp_time", "rsrq_time", "sinr_time", "prb_time",
    "rsrp_age", "rsrq_age", "sinr_age", "prb_age",
    "max_temporal_skew", "selected_action", "serving_cell", "attack_mode",
]


class ProvenanceLogger:
    def __init__(self, path: str | Path, seed: int):
        self.path = Path(path)
        self.seed = seed
        self._decision_id = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", newline="")
        self._w = csv.DictWriter(self._fh, fieldnames=COLUMNS)
        self._w.writeheader()

    def log(self, state: BuiltState, selected_action: int,
            serving_cell: Optional[int]) -> int:
        self._decision_id += 1
        ages = state.ages()
        row = {
            "seed": self.seed,
            "decision_id": self._decision_id,
            "ue_id": state.ue_id,
            "consume_time": round(state.consume_time, 6),
            "rsrp_time": round(state.source_time["rsrp"], 6),
            "rsrq_time": round(state.source_time["rsrq"], 6),
            "sinr_time": round(state.source_time["sinr"], 6),
            "prb_time": round(state.source_time["prb"], 6),
            "rsrp_age": round(ages["rsrp"], 6),
            "rsrq_age": round(ages["rsrq"], 6),
            "sinr_age": round(ages["sinr"], 6),
            "prb_age": round(ages["prb"], 6),
            "max_temporal_skew": round(state.temporal_skew(), 6),
            "selected_action": selected_action,
            "serving_cell": serving_cell if serving_cell is not None else "",
            "attack_mode": state.mode,
        }
        self._w.writerow(row)
        return self._decision_id

    def close(self) -> None:
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
