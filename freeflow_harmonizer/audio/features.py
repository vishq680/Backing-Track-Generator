from __future__ import annotations
from typing import Tuple
import numpy as np
import librosa


def load_audio_mono(path: str, sr: int = 22050) -> Tuple[np.ndarray, int, float]:
    y, sr = librosa.load(path, sr=sr, mono=True)
    duration = float(len(y) / sr)
    return y, sr, duration


def harmonic_component(y: np.ndarray) -> np.ndarray:
    y_h, _ = librosa.effects.hpss(y)
    return y_h


def compute_chroma(y: np.ndarray, sr: int, hop: int = 512) -> Tuple[np.ndarray, np.ndarray]:
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop).astype(np.float32)
    times = librosa.frames_to_time(range(chroma.shape[1]), sr=sr, hop_length=hop)
    return chroma, times


def compute_melody_pyin(y: np.ndarray, sr: int, hop: int = 512) -> Tuple[np.ndarray, np.ndarray]:
    f0, _, _ = librosa.pyin(
        y, sr=sr, hop_length=hop,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
    )
    times = librosa.frames_to_time(range(len(f0)), sr=sr, hop_length=hop)
    return f0, times
