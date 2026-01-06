from __future__ import annotations
from typing import List, Tuple
import re

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]


def _root_pc_from_chord_name(chord_name: str) -> int:
    # chord_name like "C:maj7" or "F#:min"
    root = chord_name.split(":")[0].strip().upper()
    if root not in NOTE_NAMES:
        # try normalize flats
        flats = {"DB":"C#","EB":"D#","GB":"F#","AB":"G#","BB":"A#"}
        root = flats.get(root.replace("♭","B"), root)
    return NOTE_NAMES.index(root)


def _pc_to_midi_in_range(pc: int, lo: int = 36, hi: int = 55) -> int:
    # find a midi note with pitch class pc within range
    for n in range(lo, hi + 1):
        if (n % 12) == pc:
            return n
    return lo


def render_bass(
    chord_segments: List[Tuple[float, float, str]],
    grid: dict,
    groove: str,
    velocity: int,
) -> List[Tuple[float, float, int, int]]:
    """
    Returns events: (start_sec, end_sec, midi_note, velocity)
    Simple bassline: root on each chord start, optionally a fifth near end.
    """
    step_sec = float(grid["step_sec"])
    events: List[Tuple[float, float, int, int]] = []
    g = groove.lower()

    for (t0, t1, chord_name) in chord_segments:
        root_pc = _root_pc_from_chord_name(chord_name)
        root_note = _pc_to_midi_in_range(root_pc, 36, 52)

        # root on start
        events.append((t0, min(t0 + 0.25, t1), root_note, int(velocity)))

        # optional pickup / fifth depending on style
        if (t1 - t0) > 0.6 and g in ("pop", "rock", "funk"):
            fifth_pc = (root_pc + 7) % 12
            fifth_note = _pc_to_midi_in_range(fifth_pc, 36, 52)
            t_pick = max(t0, t1 - 2 * step_sec)
            events.append((t_pick, min(t_pick + 0.20, t1), fifth_note, int(max(50, velocity - 10))))

    return events
