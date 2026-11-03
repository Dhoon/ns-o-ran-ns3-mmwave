"""Victim decision model wrapper N : state -> action (guide sections 16, 17).

The real victim is the Traffic Steering policy inside the authorized xApp.
Until the exact checkpoint is located (guide section 15), this wrapper offers
a deterministic placeholder so the attack/provenance pipeline can be tested
end-to-end. Swap `PlaceholderPolicy` for the loaded model; keep the same
`decide(state_vector) -> action` contract so aligned vs. misaligned runs use
an identical N.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol


class Policy(Protocol):
    def decide(self, state_vector: Dict[str, float]) -> int:
        """Map a feature vector to a target cell id (action)."""
        ...


@dataclass
class PlaceholderPolicy:
    """Deterministic stand-in: pick the serving-vs-candidate choice by SINR/RSRP.

    Intentionally simple and side-effect-free so that any action disagreement
    between aligned and misaligned states is attributable to the input epochs,
    not to randomness in N. Replace once the real policy is identified.
    """
    candidate_cells: List[int]

    def decide(self, state_vector: Dict[str, float]) -> int:
        # Rank candidates by a monotonic score of signal quality. With a single
        # feature vector we emulate "steer toward the better-signal cell": a
        # higher composite score keeps the first candidate, lower picks the next.
        rsrp = state_vector.get("rsrp") or 0.0
        sinr = state_vector.get("sinr") or 0.0
        prb = state_vector.get("prb") or 0.0
        score = rsrp + 2.0 * sinr - 0.5 * prb
        # Deterministic bucketing into the candidate list.
        idx = 0 if score >= 0 else min(1, len(self.candidate_cells) - 1)
        return self.candidate_cells[idx]
