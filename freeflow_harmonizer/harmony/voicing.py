from __future__ import annotations
from typing import List, Tuple


def voice_chord(pcs: Tuple[int, ...], melody_center_midi: int, max_notes: int) -> List[int]:
    max_notes = max(3, min(5, int(max_notes)))
    target_top = melody_center_midi - 3
    base = 48

    notes = sorted(set(base + ((pc - 0) % 12) for pc in pcs))

    voiced = [notes[0] - 12]
    for n in notes[1:]:
        voiced.append(n + 12)

    while len(voiced) < max_notes:
        voiced.append(voiced[-1] + 12)

    voiced = voiced[:max_notes]

    while max(voiced) > target_top and min(voiced) >= 24:
        voiced = [n - 12 for n in voiced]

    return [int(n) for n in voiced]
