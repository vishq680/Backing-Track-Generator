from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
NOTE_ALIASES = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}

CHORD_TYPES: Dict[str, Tuple[int, ...]] = {
    "maj":   (0, 4, 7),
    "min":   (0, 3, 7),
    "sus2":  (0, 2, 7),
    "sus4":  (0, 5, 7),

    "7":     (0, 4, 7, 10),
    "maj7":  (0, 4, 7, 11),
    "min7":  (0, 3, 7, 10),
    "m7b5":  (0, 3, 6, 10),

    "add9":  (0, 4, 7, 2),
    "madd9": (0, 3, 7, 2),
    "maj9":  (0, 4, 7, 11, 2),
    "min9":  (0, 3, 7, 10, 2),
}

CHORD_COMPLEXITY = {
    "maj": 0.0, "min": 0.0, "sus2": 0.1, "sus4": 0.1,
    "7": 0.15, "maj7": 0.15, "min7": 0.15, "m7b5": 0.22,
    "add9": 0.22, "madd9": 0.22, "maj9": 0.35, "min9": 0.35,
}


def pc_name(pc: int) -> str:
    return NOTE_NAMES[int(pc) % 12]


@dataclass(frozen=True)
class ChordCandidate:
    name: str
    pcs: Tuple[int, ...]
    complexity: float


def parse_key(key_str: str) -> Optional[Tuple[int, str]]:
    s = key_str.strip()
    if not s:
        return None
    s = s.replace("major", "maj").replace("minor", "min")
    s = " ".join(s.split())
    parts = s.split(" ")
    if len(parts) < 2:
        raise ValueError("Key format: 'D min', 'Bb maj', 'F# min'.")

    root = parts[0].upper().replace("♭", "B").replace("♯", "#")
    mode = parts[1].lower()
    if mode not in ("maj", "min"):
        raise ValueError("Mode must be 'maj' or 'min'.")

    root = NOTE_ALIASES.get(root, root)
    if root not in NOTE_NAMES:
        raise ValueError(f"Unknown key root: {root}")

    return NOTE_NAMES.index(root), mode


def estimate_key_krumhansl(chroma_mean: np.ndarray) -> Tuple[int, str]:
    major_profile = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88], dtype=np.float32)
    minor_profile = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17], dtype=np.float32)
    major_profile /= major_profile.sum()
    minor_profile /= minor_profile.sum()

    c = chroma_mean.astype(np.float32)
    c = c / (c.sum() + 1e-8)

    best = None
    for mode, prof in [("maj", major_profile), ("min", minor_profile)]:
        for root in range(12):
            score = float(np.dot(c, np.roll(prof, root)))
            if best is None or score > best[0]:
                best = (score, root, mode)
    _, root, mode = best
    return int(root), mode


def diatonic_scale_roots(key_root: int, mode: str) -> List[int]:
    if mode == "maj":
        scale = [0, 2, 4, 5, 7, 9, 11]
    else:
        scale = [0, 2, 3, 5, 7, 8, 10]
    return [int((key_root + s) % 12) for s in scale]


def build_candidates(
    key: Optional[Tuple[int, str]],
    scope: str,
    richness: str,
    style: str,
    chroma_mean: np.ndarray
) -> List[ChordCandidate]:
    if key is None and scope == "diatonic":
        key = estimate_key_krumhansl(chroma_mean)

    allowed_roots = list(range(12))
    if scope == "diatonic" and key is not None:
        allowed_roots = diatonic_scale_roots(key[0], key[1])

    triads = ["maj", "min"]
    sevenths = ["7", "maj7", "min7", "m7b5"]
    colors = ["sus2", "sus4", "add9", "madd9", "maj9", "min9"]

    if richness == "basic":
        chord_types = triads
    elif richness == "rich":
        chord_types = triads + sevenths
    else:
        chord_types = triads + sevenths + colors

    if style in ("classical", "pop"):
        chord_types = [t for t in chord_types if t not in ("m7b5",)]
        if richness == "rich":
            chord_types = [t for t in chord_types if t != "7"]

    cands: List[ChordCandidate] = []
    for r in allowed_roots:
        for t in chord_types:
            pcs = tuple(sorted(((r + i) % 12) for i in CHORD_TYPES[t]))
            cands.append(ChordCandidate(
                name=f"{pc_name(r)}:{t}",
                pcs=pcs,
                complexity=CHORD_COMPLEXITY.get(t, 0.2)
            ))

    if not cands:
        for r in allowed_roots:
            for t in ("maj", "min"):
                pcs = tuple(sorted(((r + i) % 12) for i in CHORD_TYPES[t]))
                cands.append(ChordCandidate(f"{pc_name(r)}:{t}", pcs, CHORD_COMPLEXITY[t]))

    return cands
