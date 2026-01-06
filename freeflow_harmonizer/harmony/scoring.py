from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np
from .vocab import ChordCandidate


def chord_template_vec(pcs) -> np.ndarray:
    v = np.zeros(12, dtype=np.float32)
    for p in pcs:
        v[int(p) % 12] = 1.0
    return v


def score_candidate(chroma_vec: np.ndarray, melody_pcs: List[int], cand: ChordCandidate, weights: Dict[str, float]) -> float:
    cscore = float(np.dot(chroma_vec, chord_template_vec(cand.pcs))) * float(weights["w_chroma"])

    if melody_pcs:
        pcs_set = set(cand.pcs)
        hits = sum((p in pcs_set) for p in melody_pcs)
        ratio = hits / max(1, len(melody_pcs))
        mscore = (float(weights["w_mel_hit"]) * ratio) - (float(weights["w_mel_miss"]) * (1.0 - ratio))
    else:
        mscore = 0.0

    kpen = float(weights["w_complexity"]) * float(cand.complexity)
    return cscore + mscore - kpen


def choose_chord(
    chroma_vec: np.ndarray,
    melody_pcs: List[int],
    candidates: List[ChordCandidate],
    prev_idx: Optional[int],
    change_penalty: float,
    weights: Dict[str, float],
) -> int:
    scores = np.array([score_candidate(chroma_vec, melody_pcs, c, weights) for c in candidates], dtype=np.float32)

    if prev_idx is not None:
        scores -= float(change_penalty)
        scores[prev_idx] += float(change_penalty)

    return int(np.argmax(scores))
