from __future__ import annotations
from typing import Tuple
import numpy as np
import librosa


def estimate_tempo_and_beats(y: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
    """
    Returns:
      tempo_bpm: float
      beat_times: (B,) seconds
    """
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    # tempo can sometimes come back as an array; normalize
    tempo_bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])
    return tempo_bpm, beat_times
