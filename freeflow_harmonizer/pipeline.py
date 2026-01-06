from __future__ import annotations
import json
from typing import List, Optional, Tuple
import numpy as np
import librosa

from .config import RunConfig
from .audio.features import load_audio_mono, harmonic_component, compute_chroma, compute_melody_pyin
from .segmentation.methods import segment_fixed, segment_onsets, segment_auto
from .harmony.vocab import build_candidates, parse_key, estimate_key_krumhansl, pc_name
from .harmony.scoring import choose_chord

from .midi.types import SegmentChord, TempoChordSegment
from .midi.writer_freeflow import write_chords_freeflow
from .midi.writer_tempo import write_backing_tempo

from .tempo.tempo_detect import estimate_tempo_and_beats
from .tempo.grid import parse_time_signature, build_grid
from .patterns.drums import render_drums
from .patterns.bass import render_bass


def mean_chroma_in_window(chroma: np.ndarray, chroma_times: np.ndarray, t0: float, t1: float) -> np.ndarray:
    idx = np.where((chroma_times >= t0) & (chroma_times < t1))[0]
    if len(idx) == 0:
        return np.zeros(12, dtype=np.float32)
    v = np.mean(chroma[:, idx], axis=1).astype(np.float32)
    return v / (v.sum() + 1e-8)


def melody_pcs_in_window(f0: np.ndarray, f0_times: np.ndarray, t0: float, t1: float) -> Tuple[List[int], Optional[int]]:
    idx = np.where((f0_times >= t0) & (f0_times < t1))[0]
    vals = f0[idx]
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return [], None
    midi = librosa.hz_to_midi(vals)
    midi = np.clip(np.round(midi), 0, 127).astype(int)
    pcs = [int(n) % 12 for n in midi.tolist()]
    center = int(np.median(midi))
    return pcs, center


def run_freeflow(cfg: RunConfig):
    y, sr, duration = load_audio_mono(cfg.audio_path, sr=22050)
    y_use = harmonic_component(y) if cfg.harmony.use_hpss else y

    chroma, chroma_times = compute_chroma(y_use, sr)
    chroma_mean = np.mean(chroma, axis=1)

    key = parse_key(cfg.harmony.key_str) if cfg.harmony.key_str.strip() else None
    candidates = build_candidates(
        key=key,
        scope=cfg.harmony.scope,
        richness=cfg.harmony.richness,
        style=cfg.harmony.style,
        chroma_mean=chroma_mean
    )

    f0, f0_times = (None, None)
    if cfg.harmony.use_melody:
        f0, f0_times = compute_melody_pyin(y_use, sr)

    seg_mode = cfg.segmentation.mode
    if seg_mode == "fixed":
        windows = segment_fixed(duration, cfg.segmentation.fixed_seg_sec)
    elif seg_mode == "onsets":
        windows = segment_onsets(y_use, sr, duration, cfg.segmentation.min_seg_sec)
    else:
        windows = segment_auto(y_use, sr, duration, cfg.segmentation.min_seg_sec, cfg.segmentation.fixed_seg_sec)

    if cfg.harmony.input_type == "melody" and len(windows) < 3:
        windows = segment_fixed(duration, max(1.5, cfg.segmentation.fixed_seg_sec))

    weights = {
        "w_chroma": cfg.weights.w_chroma,
        "w_mel_hit": cfg.weights.w_mel_hit,
        "w_mel_miss": cfg.weights.w_mel_miss,
        "w_complexity": cfg.weights.w_complexity,
    }

    segments: List[SegmentChord] = []
    prev_idx: Optional[int] = None

    for (t0, t1) in windows:
        cvec = mean_chroma_in_window(chroma, chroma_times, t0, t1)
        mel_pcs, mel_center = ([], None)
        if cfg.harmony.use_melody and f0 is not None and f0_times is not None:
            mel_pcs, mel_center = melody_pcs_in_window(f0, f0_times, t0, t1)

        idx = choose_chord(cvec, mel_pcs, candidates, prev_idx, cfg.harmony.change_penalty, weights)
        prev_idx = idx
        cand = candidates[idx]
        segments.append(SegmentChord(float(t0), float(t1), cand.name, cand.pcs, mel_center))

    if segments and segments[-1].end < duration:
        segments[-1] = SegmentChord(segments[-1].start, float(duration), segments[-1].chord_name, segments[-1].pcs, segments[-1].melody_center)

    write_chords_freeflow(cfg.out_midi, segments, cfg.freeflow_midi)

    key_est_root, key_est_mode = estimate_key_krumhansl(chroma_mean)
    report = {
        "mode": "freeflow",
        "audio": cfg.audio_path,
        "duration_sec": float(duration),
        "estimated_key": f"{pc_name(key_est_root)} {key_est_mode}",
        "segments": [{"start": s.start, "end": s.end, "chord": s.chord_name} for s in segments],
        "config": {
            "harmony": cfg.harmony.__dict__,
            "segmentation": cfg.segmentation.__dict__,
            "weights": cfg.weights.__dict__,
            "midi": cfg.freeflow_midi.__dict__,
        }
    }
    with open(cfg.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n--- FREEFLOW done ---")
    print(f"Wrote MIDI: {cfg.out_midi}")
    print(f"Wrote JSON: {cfg.out_json}")
    print("Ableton: add an instrument to the MIDI track (MIDI is silent).")


def _build_chord_segments_tempo(cfg: RunConfig, grid: dict, chroma: np.ndarray, chroma_times: np.ndarray, candidates, weights) -> List[TempoChordSegment]:
    """
    Build chord segments aligned to bar/beat grid.
    chord_rate:
      - 1_bar: one chord per bar
      - 2_bars: one chord every 2 bars
      - 2_beats: chord change every 2 beats (approx)
    """
    bar_starts = grid["bar_starts"]
    beat_sec = grid["beat_sec"]
    duration = bar_starts[-1]

    # Create segment boundaries
    if cfg.tempo.chord_rate == "2_bars":
        boundaries = bar_starts[::2]
        if boundaries[-1] < bar_starts[-1]:
            boundaries.append(bar_starts[-1])
    elif cfg.tempo.chord_rate == "2_beats":
        # approximate: 2 quarter-beat seconds
        step = 2.0 * beat_sec
        boundaries = [0.0]
        t = 0.0
        while t < duration - 1e-3:
            t = min(duration, t + step)
            boundaries.append(t)
    else:
        boundaries = bar_starts

    # Ensure last is audio duration-ish
    # We'll keep within actual duration from chroma_times end
    max_t = float(chroma_times[-1]) if len(chroma_times) else boundaries[-1]
    boundaries = [b for b in boundaries if b <= max_t + 1e-3]
    if boundaries[-1] < max_t:
        boundaries.append(max_t)

    segments: List[TempoChordSegment] = []
    prev_idx: Optional[int] = None

    for i in range(len(boundaries) - 1):
        t0, t1 = float(boundaries[i]), float(boundaries[i + 1])
        if t1 <= t0 + 0.05:
            continue
        cvec = mean_chroma_in_window(chroma, chroma_times, t0, t1)
        # In tempo mode we may not do melody conditioning (depends on input); keep melody empty for now
        mel_pcs: List[int] = []
        idx = choose_chord(cvec, mel_pcs, candidates, prev_idx, cfg.harmony.change_penalty, weights)
        prev_idx = idx
        cand = candidates[idx]
        segments.append(TempoChordSegment(t0, t1, cand.name, cand.pcs))

    return segments


def run_tempo(cfg: RunConfig):
    y, sr, duration = load_audio_mono(cfg.audio_path, sr=22050)
    y_use = harmonic_component(y) if cfg.harmony.use_hpss else y

    bpm = cfg.tempo.bpm
    if bpm is None:
        bpm_est, beat_times = estimate_tempo_and_beats(y_use, sr)
        bpm = float(bpm_est)
    ts = parse_time_signature(cfg.tempo.time_signature)

    grid = build_grid(bpm=bpm, duration_sec=duration, ts=ts, subdivision=cfg.tempo.subdivision)

    chroma, chroma_times = compute_chroma(y_use, sr)
    chroma_mean = np.mean(chroma, axis=1)
    key = parse_key(cfg.harmony.key_str) if cfg.harmony.key_str.strip() else None
    candidates = build_candidates(
        key=key,
        scope=cfg.harmony.scope,
        richness=cfg.harmony.richness,
        style=cfg.harmony.style,
        chroma_mean=chroma_mean
    )

    weights = {
        "w_chroma": max(0.6, cfg.weights.w_chroma),   # tempo mode uses chroma more
        "w_mel_hit": cfg.weights.w_mel_hit,
        "w_mel_miss": cfg.weights.w_mel_miss,
        "w_complexity": cfg.weights.w_complexity,
    }

    chord_segments = _build_chord_segments_tempo(cfg, grid, chroma, chroma_times, candidates, weights)

    # Convert for bass generator interface
    chord_segments_simple = [(s.start, s.end, s.chord_name) for s in chord_segments]

    bass_events = []
    drum_events = []

    if cfg.tempo.include_bass:
        bass_events = render_bass(
            chord_segments=chord_segments_simple,
            grid=grid,
            groove=cfg.tempo.groove,
            velocity=cfg.tempo_midi.velocity_bass
        )

    if cfg.tempo.include_drums:
        drum_events = render_drums(
            grid=grid,
            groove=cfg.tempo.groove,
            velocity=cfg.tempo_midi.velocity_drums
        )

    if not cfg.tempo.include_chords:
        chord_segments = []

    write_backing_tempo(
        out_midi=cfg.out_midi,
        bpm=bpm,
        ts=ts,
        chord_segments=chord_segments,
        bass_events=bass_events,
        drum_events=drum_events,
        midi=cfg.tempo_midi,
    )

    key_est_root, key_est_mode = estimate_key_krumhansl(chroma_mean)
    report = {
        "mode": "tempo",
        "audio": cfg.audio_path,
        "duration_sec": float(duration),
        "bpm": float(bpm),
        "time_signature": cfg.tempo.time_signature,
        "subdivision": cfg.tempo.subdivision,
        "estimated_key": f"{pc_name(key_est_root)} {key_est_mode}",
        "chords": [{"start": s.start, "end": s.end, "chord": s.chord_name} for s in chord_segments],
        "config": {
            "harmony": cfg.harmony.__dict__,
            "tempo": cfg.tempo.__dict__,
            "weights": cfg.weights.__dict__,
            "midi": cfg.tempo_midi.__dict__,
        }
    }
    with open(cfg.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n--- TEMPO done ---")
    print(f"BPM: {bpm:.2f} | TS: {cfg.tempo.time_signature} | Groove: {cfg.tempo.groove}")
    print(f"Wrote MIDI: {cfg.out_midi}")
    print(f"Wrote JSON: {cfg.out_json}")
    print("Ableton: set tempo to the same BPM (or warp) for best alignment.")


def run(cfg: RunConfig):
    if cfg.mode == "tempo":
        return run_tempo(cfg)
    return run_freeflow(cfg)
