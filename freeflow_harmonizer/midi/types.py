from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class SegmentChord:
    # freeflow chords segment
    start: float
    end: float
    chord_name: str
    pcs: Tuple[int, ...]
    melody_center: Optional[int]


@dataclass(frozen=True)
class TempoChordSegment:
    # tempo-grid chord segment
    start: float
    end: float
    chord_name: str
    pcs: Tuple[int, ...]
