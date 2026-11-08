"""Attack-mode selection and critical-time logic (guide sections 22, 24).

This module decides, per decision epoch, *whether* to misalign and *which*
lag profile to apply. It never touches KPM values or the policy weights; it
only chooses which genuine epoch each feature is read from.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from kpm_buffer import Snapshot
from state_builder import (
    FEATURES, BuiltState,
    build_state_aligned, build_state_uniform_lag,
    build_state_feature_lag, build_state_random_feature_lag,
)


@dataclass
class AttackConfig:
    # one of: B0 aligned, B1 uniform, A1/A2 feature_lag, A3 random, A4 selective
    mode: str = "aligned"
    uniform_k: int = 1                       # for B1
    feature_lag: Dict[str, int] = field(default_factory=dict)  # for A1/A2
    max_k: int = 5                           # for A3 random
    # A4 selective:
    selective_base: str = "feature_lag"      # lag profile applied when critical
    criticality_threshold: float = 0.0
    seed: int = 0


def _criticality(history: List[Snapshot]) -> float:
    """g_t: proxy criticality score (guide section 22).

    Uses serving/candidate SINR proximity via recent SINR trend magnitude.
    Replace with a policy-confidence / Q-margin signal once the victim model
    N exposes action values. Kept measurement-only so it needs no model hook.
    """
    if len(history) < 2:
        return 0.0
    s_now = history[-1].sinr
    s_prev = history[-2].sinr
    if s_now is None or s_prev is None:
        return 0.0
    return abs(s_now - s_prev)  # rapid change near a boundary => more critical


class AttackController:
    def __init__(self, cfg: AttackConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.attacked_epochs = 0
        self.total_epochs = 0

    def build(self, history: List[Snapshot], consume_time: float,
              ue_id: int) -> BuiltState:
        self.total_epochs += 1
        m = self.cfg.mode

        if m in ("aligned", "B0"):
            return build_state_aligned(history, consume_time, ue_id)

        if m in ("uniform", "B1", "uniform_lag"):
            self.attacked_epochs += 1
            return build_state_uniform_lag(history, consume_time, ue_id,
                                           self.cfg.uniform_k)

        if m in ("feature_lag", "A1", "A2"):
            self.attacked_epochs += 1
            lag = self.cfg.feature_lag or {f: 0 for f in FEATURES}
            return build_state_feature_lag(history, consume_time, ue_id, lag)

        if m in ("random", "A3", "random_feature_lag"):
            self.attacked_epochs += 1
            return build_state_random_feature_lag(history, consume_time, ue_id,
                                                  self.cfg.max_k, self.rng)

        if m in ("selective", "A4"):
            g = _criticality(history)
            if g >= self.cfg.criticality_threshold:
                self.attacked_epochs += 1
                if self.cfg.selective_base == "uniform":
                    st = build_state_uniform_lag(history, consume_time, ue_id,
                                                 self.cfg.uniform_k)
                elif self.cfg.selective_base == "random":
                    st = build_state_random_feature_lag(history, consume_time,
                                                        ue_id, self.cfg.max_k,
                                                        self.rng)
                else:
                    lag = self.cfg.feature_lag or {f: 0 for f in FEATURES}
                    st = build_state_feature_lag(history, consume_time, ue_id, lag)
                st.mode = "selective_attack"
                return st
            return build_state_aligned(history, consume_time, ue_id)

        raise ValueError(f"unknown attack mode: {m}")

    @property
    def attack_rate(self) -> float:
        return self.attacked_epochs / self.total_epochs if self.total_epochs else 0.0
