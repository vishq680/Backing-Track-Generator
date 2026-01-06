from __future__ import annotations
from typing import List, Tuple

# GM drum note numbers
KICK = 36
SNARE = 38
HHC = 42  # closed hat


def _pattern_for_groove(groove: str, steps_per_bar: int) -> dict:
    """
    Returns drum pattern in step indices within a bar:
      kick_steps, snare_steps, hat_steps
    steps_per_bar depends on subdivision and time signature.

    We implement patterns assuming 4/4-ish feel, but they still "fit" any steps_per_bar:
    - Kick: on bar start, mid bar
    - Snare: roughly quarter-beat backbeat
    - Hat: every step (or every other)
    """
    g = groove.lower()

    # hats: every step for 1/8 grid; for 1/16 it can be dense but ok
    hat_steps = list(range(steps_per_bar))

    # approximate quarter positions within bar
    # for 4/4 with 1/8 subdivision => steps_per_bar=8, quarters at 0,2,4,6
    quarter = max(1, steps_per_bar // 4)

    if g == "funk":
        kick_steps = [0, 2 * quarter, 3 * quarter]  # some syncopation
        snare_steps = [quarter, 3 * quarter]
    elif g == "edm":
        kick_steps = [0, 2 * quarter]  # four-on-floor-ish simplified
        snare_steps = [2 * quarter]    # clap on 3, simple
    elif g == "rock":
        kick_steps = [0, 2 * quarter]
        snare_steps = [quarter, 3 * quarter]
    else:  # pop default
        kick_steps = [0, 2 * quarter]
        snare_steps = [quarter, 3 * quarter]

    kick_steps = [s for s in kick_steps if 0 <= s < steps_per_bar]
    snare_steps = [s for s in snare_steps if 0 <= s < steps_per_bar]
    return {"kick": kick_steps, "snare": snare_steps, "hat": hat_steps}


def render_drums(
    grid: dict,
    groove: str,
    velocity: int,
) -> List[Tuple[float, float, int, int]]:
    """
    Returns list of events: (start_sec, end_sec, midi_note, velocity)
    Channel handled by MIDI writer.
    """
    step_sec = float(grid["step_sec"])
    steps_per_bar = int(grid["steps_per_bar"])
    bar_starts = grid["bar_starts"]

    pat = _pattern_for_groove(groove, steps_per_bar)
    events: List[Tuple[float, float, int, int]] = []

    for b0 in bar_starts[:-1]:
        # Kick / snare: short notes
        for s in pat["kick"]:
            t = b0 + s * step_sec
            events.append((t, t + 0.05, KICK, int(velocity)))
        for s in pat["snare"]:
            t = b0 + s * step_sec
            events.append((t, t + 0.05, SNARE, int(velocity)))
        # Hat: slightly shorter
        for s in pat["hat"]:
            t = b0 + s * step_sec
            events.append((t, t + 0.03, HHC, int(max(40, velocity - 20))))

    return events
