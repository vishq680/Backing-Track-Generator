from __future__ import annotations
from typing import List, Tuple
import numpy as np
import librosa


def segment_fixed(duration: float, seg_sec: float) -> List[Tuple[float, float]]:
    segs = []
    t = 0.0
    while t < duration - 1e-3:
        t1 = min(duration, t + seg_sec)
        if t1 - t >= 0.05:
            segs.append((t, t1))
        t = t1
    return segs


def segment_onsets(y: np.ndarray, sr: int, duration: float, min_seg_sec: float) -> List[Tuple[float, float]]:
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames", backtrack=False)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    points = [0.0] + [float(t) for t in onset_times if 0.0 < t < duration] + [float(duration)]
    points = sorted(set(points))

    segs = []
    cur0 = points[0]
    for i in range(1, len(points)):
        cur1 = points[i]
        if (cur1 - cur0) < min_seg_sec and i < len(points) - 1:
            continue
        segs.append((cur0, cur1))
        cur0 = cur1

    if len(segs) <= 1:
        return segment_fixed(duration, max(min_seg_sec, 1.5))
    return segs


def segment_auto(y: np.ndarray, sr: int, duration: float, min_seg_sec: float, fixed_sec: float) -> List[Tuple[float, float]]:
    segs = segment_onsets(y, sr, duration, min_seg_sec)
    if len(segs) >= 3:
        return segs
    return segment_fixed(duration, fixed_sec)
