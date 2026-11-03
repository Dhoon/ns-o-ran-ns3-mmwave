"""Per-UE timestamped KPM history buffer (guide section 13, 18).

Stores genuine, unmodified KPM measurements per UE in a bounded deque.
The original measurement timestamp is never overwritten: the temporal-
misalignment experiment only ever *selects which genuine epoch* to read,
it does not fabricate or mutate any measured value.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, List


@dataclass
class Snapshot:
    """One genuine KPM measurement epoch for one UE.

    `sim_time` is the measurement/reporting time as reported over E2. It is
    the provenance anchor and must never be rewritten after insertion.
    """
    sim_time: float
    ue_id: int
    serving_cell: Optional[int] = None
    rsrp: Optional[float] = None
    rsrq: Optional[float] = None
    sinr: Optional[float] = None
    prb: Optional[float] = None
    throughput: Optional[float] = None
    extra: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict:
        d = asdict(self)
        extra = d.pop("extra")
        d.update(extra)
        return d


class KpmHistoryBuffer:
    """Bounded per-UE history of genuine KPM snapshots.

    H is the number of reports retained per UE. It must be large enough to
    cover the maximum feature lag you intend to apply (see state_builder).
    """

    def __init__(self, maxlen: int = 32):
        if maxlen < 1:
            raise ValueError("maxlen must be >= 1")
        self.maxlen = maxlen
        self._hist: Dict[int, deque] = {}

    def append(self, snap: Snapshot) -> None:
        """Insert a genuine measurement. Values and timestamps are untouched."""
        dq = self._hist.get(snap.ue_id)
        if dq is None:
            dq = deque(maxlen=self.maxlen)
            self._hist[snap.ue_id] = dq
        dq.append(snap)

    def history(self, ue_id: int) -> List[Snapshot]:
        """Oldest-first list of retained snapshots for a UE."""
        dq = self._hist.get(ue_id)
        return list(dq) if dq else []

    def latest(self, ue_id: int) -> Optional[Snapshot]:
        dq = self._hist.get(ue_id)
        return dq[-1] if dq else None

    def depth(self, ue_id: int) -> int:
        dq = self._hist.get(ue_id)
        return len(dq) if dq else 0

    def ues(self) -> List[int]:
        return list(self._hist.keys())
