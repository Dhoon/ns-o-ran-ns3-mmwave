"""State construction A : KPM history -> decision state (guide sections 17, 19-22).

This is attack surface A. Every builder returns BOTH:
  * a feature vector (what the victim policy N consumes), and
  * a provenance record (which genuine measurement epoch produced each feature).

Core invariant for the paper:
  Only the *selection of which genuine epoch* changes between aligned and
  misaligned modes. No KPM value is ever altered, and the victim policy N,
  topology, traffic, permissions, and control interface stay identical.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from kpm_buffer import Snapshot

# Canonical feature order fed to the victim policy. Must match N's expected input.
FEATURES: Sequence[str] = ("rsrp", "rsrq", "sinr", "prb")


@dataclass
class BuiltState:
    consume_time: float          # when the xApp assembles/consumes this state
    ue_id: int
    vector: Dict[str, float]     # feature name -> genuine value
    source_time: Dict[str, float]  # feature name -> genuine measurement epoch
    lag_reports: Dict[str, int]  # feature name -> k (reports back from newest)
    mode: str

    def ages(self) -> Dict[str, float]:
        """Age_i = t_consume - t_i (seconds), per feature (guide section 23)."""
        return {f: self.consume_time - self.source_time[f] for f in self.vector}

    def temporal_skew(self) -> float:
        """max_i(t_i) - min_i(t_i): spread across the epochs used (guide section 23)."""
        ts = list(self.source_time.values())
        return (max(ts) - min(ts)) if ts else 0.0


def _pick(history: List[Snapshot], k: int) -> Snapshot:
    """Return the snapshot k reports before the newest (k=0 => newest).

    Clamps to the oldest retained snapshot if history is shallower than k,
    so a short buffer degrades gracefully instead of raising.
    """
    if not history:
        raise ValueError("empty history for UE")
    idx = len(history) - 1 - k
    if idx < 0:
        idx = 0
    return history[idx]


def _assemble(history: List[Snapshot], lag: Dict[str, int],
              consume_time: float, ue_id: int, mode: str) -> BuiltState:
    vector, source_time, lag_reports = {}, {}, {}
    for f in FEATURES:
        k = int(lag.get(f, 0))
        snap = _pick(history, k)
        val = getattr(snap, f)
        if val is None:
            val = snap.extra.get(f)
        vector[f] = val
        source_time[f] = snap.sim_time
        lag_reports[f] = k
    return BuiltState(consume_time, ue_id, vector, source_time, lag_reports, mode)


# --- Mode 0: aligned baseline (guide section 19) -------------------------------
def build_state_aligned(history: List[Snapshot], consume_time: float,
                        ue_id: int) -> BuiltState:
    """z_t = A_aligned(W_t): every feature from the newest epoch K_t."""
    return _assemble(history, {f: 0 for f in FEATURES}, consume_time, ue_id,
                     "aligned")


# --- Mode 1: uniform stale state (guide section 20) ----------------------------
def build_state_uniform_lag(history: List[Snapshot], consume_time: float,
                            ue_id: int, k: int) -> BuiltState:
    """z'_t = K_(t-k): all features from one older epoch."""
    return _assemble(history, {f: k for f in FEATURES}, consume_time, ue_id,
                     f"uniform_lag_k{k}")


# --- Mode 2: feature-wise temporal misalignment (guide section 21) -------------
def build_state_feature_lag(history: List[Snapshot], consume_time: float,
                            ue_id: int, lag: Dict[str, int]) -> BuiltState:
    """z'_t = [K_RSRP(t-k1), K_RSRQ(t-k2), ...] with not all k_i equal."""
    return _assemble(history, lag, consume_time, ue_id, "feature_lag")


def build_state_random_feature_lag(history: List[Snapshot], consume_time: float,
                                   ue_id: int, max_k: int,
                                   rng: Optional[random.Random] = None) -> BuiltState:
    """A3: independent random lag per feature in [0, max_k]."""
    r = rng or random
    lag = {f: r.randint(0, max_k) for f in FEATURES}
    st = _assemble(history, lag, consume_time, ue_id, "random_feature_lag")
    return st
