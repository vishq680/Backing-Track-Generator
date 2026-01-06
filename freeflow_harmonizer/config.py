from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Weights:
    # For melody-only harmonization: melody fit dominates
    w_chroma: float = 0.25
    w_mel_hit: float = 0.95
    w_mel_miss: float = 0.60
    w_complexity: float = 0.18


@dataclass(frozen=True)
class HarmonyConfig:
    input_type: str = "melody"      # melody or mixed
    style: str = "film"             # classical/film/pop/jazz
    richness: str = "lush"          # basic/rich/lush
    scope: str = "diatonic"         # diatonic or all_roots
    key_str: str = ""               # optional "D min"
    change_penalty: float = 0.05
    use_hpss: bool = True
    use_melody: bool = True


@dataclass(frozen=True)
class SegmentationConfig:
    # used in freeflow mode
    mode: str = "onsets"            # auto/onsets/fixed
    fixed_seg_sec: float = 2.0
    min_seg_sec: float = 0.8


@dataclass(frozen=True)
class FreeflowMidiConfig:
    # 60BPM + 1000 TPQN => 1 tick = 1ms
    tpqn: int = 1000
    bpm: int = 60
    channel: int = 0
    program: int = 0
    velocity: int = 72
    max_notes_per_chord: int = 5  # 3..5


@dataclass(frozen=True)
class TempoConfig:
    bpm: Optional[float] = None          # None => estimate
    time_signature: str = "4/4"          # e.g., "7/8"
    subdivision: str = "1/8"             # "1/8" or "1/16"
    chord_rate: str = "1_bar"            # "1_bar", "2_bars", "2_beats"
    groove: str = "pop"                  # pop/rock/funk/edm (simple patterns)
    include_drums: bool = True
    include_bass: bool = True
    include_chords: bool = True


@dataclass(frozen=True)
class TempoMidiConfig:
    # Standard MIDI timing for tempo-grid mode
    tpqn: int = 480
    channel_chords: int = 0
    channel_bass: int = 1
    channel_drums: int = 9  # GM drums channel = 10 => zero-based 9
    program_chords: int = 0
    program_bass: int = 33  # Acoustic Bass in GM
    velocity_chords: int = 70
    velocity_bass: int = 78
    velocity_drums: int = 90
    max_notes_per_chord: int = 4


@dataclass(frozen=True)
class RunConfig:
    mode: str
    audio_path: str
    out_midi: str
    out_json: str

    harmony: HarmonyConfig = HarmonyConfig()
    weights: Weights = Weights()

    segmentation: SegmentationConfig = SegmentationConfig()
    freeflow_midi: FreeflowMidiConfig = FreeflowMidiConfig()

    tempo: TempoConfig = TempoConfig()
    tempo_midi: TempoMidiConfig = TempoMidiConfig()
