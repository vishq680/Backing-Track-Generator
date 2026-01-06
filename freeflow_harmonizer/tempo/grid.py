from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math


@dataclass(frozen=True)
class TimeSignature:
    numerator: int
    denominator: int


def parse_time_signature(ts: str) -> TimeSignature:
    s = ts.strip()
    if "/" not in s:
        raise ValueError("Time signature must look like '4/4' or '7/8'")
    a, b = s.split("/", 1)
    num = int(a.strip())
    den = int(b.strip())
    if num <= 0 or den not in (1, 2, 4, 8, 16, 32):
        raise ValueError("Unsupported time signature denominator. Use 1/2/4/8/16/32.")
    return TimeSignature(num, den)


def build_grid(
    bpm: float,
    duration_sec: float,
    ts: TimeSignature,
    subdivision: str,
) -> dict:
    """
    Build a simple constant-tempo grid.
    Returns dict with:
      beat_sec: seconds per beat (quarter note)
      step_sec: seconds per step (subdivision)
      steps_per_bar: int
      bar_starts: [sec]
      step_times: [sec]
    Assumes 1 beat = quarter note.
    """
    beat_sec = 60.0 / float(bpm)

    # Determine steps per beat based on subdivision
    # subdivision is like "1/8" or "1/16" meaning eighth or sixteenth notes.
    sub = subdivision.strip()
    if sub == "1/8":
        steps_per_quarter = 2
    elif sub == "1/16":
        steps_per_quarter = 4
    else:
        steps_per_quarter = 2

    # Time signature denominator tells what note gets the beat.
    # We'll translate bar length in quarter-note beats:
    # bar_quarters = numerator * (4 / denominator)
    bar_quarters = ts.numerator * (4.0 / ts.denominator)
    bar_sec = bar_quarters * beat_sec

    step_sec = beat_sec / steps_per_quarter
    steps_per_bar = int(round(bar_sec / step_sec))

    # Build lists
    num_steps = int(math.ceil(duration_sec / step_sec))
    step_times = [i * step_sec for i in range(num_steps + 1)]

    num_bars = int(math.ceil(duration_sec / bar_sec))
    bar_starts = [i * bar_sec for i in range(num_bars + 1)]

    return {
        "bpm": float(bpm),
        "time_signature": {"numerator": ts.numerator, "denominator": ts.denominator},
        "subdivision": subdivision,
        "beat_sec": beat_sec,
        "step_sec": step_sec,
        "steps_per_bar": steps_per_bar,
        "bar_sec": bar_sec,
        "bar_starts": bar_starts,
        "step_times": step_times,
    }
