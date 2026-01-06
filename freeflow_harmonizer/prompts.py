from __future__ import annotations
from typing import Optional

from .config import (
    RunConfig, HarmonyConfig, Weights,
    SegmentationConfig, FreeflowMidiConfig,
    TempoConfig, TempoMidiConfig
)


def _prompt(text: str, default: Optional[str] = None) -> str:
    if default is None:
        return input(f"{text}: ").strip()
    ans = input(f"{text} [{default}]: ").strip()
    return ans if ans else default


def _yesno(text: str, default: bool) -> bool:
    d = "Y/n" if default else "y/N"
    ans = input(f"{text} ({d}): ").strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes", "1", "true", "t")


def build_run_config_interactive(audio_path: Optional[str] = None) -> RunConfig:
    print("\n=== Backing Track Generator ===")
    mode = _prompt("Mode: freeflow (rubato chords-only) or tempo (grid chords+bass+drums)", "freeflow").lower()
    if mode not in ("freeflow", "tempo"):
        mode = "freeflow"

    audio = audio_path or _prompt("Audio path (wav recommended)", None)
    out_midi = _prompt("Output MIDI filename", "backing.mid")
    out_json = _prompt("Output JSON report filename", "report.json")

    # Shared musical preferences
    input_type = _prompt("Input type: melody (solo) or mixed", "melody").lower()
    if input_type not in ("melody", "mixed"):
        input_type = "melody"

    style = _prompt("Style bias: classical / film / pop / jazz", "film").lower()
    if style not in ("classical", "film", "pop", "jazz", "jazz-ish"):
        style = "film"

    richness = _prompt("Harmony richness: basic / rich / lush", "lush").lower()
    if richness not in ("basic", "rich", "lush"):
        richness = "lush"

    scope = _prompt("Chord root scope: diatonic or all_roots", "diatonic").lower()
    if scope not in ("diatonic", "all_roots"):
        scope = "diatonic"

    key_str = _prompt("Optional key (e.g., 'D min', 'Bb maj') or leave blank to auto", "")

    use_hpss = _yesno("Use HPSS harmonic extraction?", True)
    use_melody = _yesno("Use melody conditioning (pyin)?", default=(input_type == "melody"))

    change_penalty = float(_prompt("Change penalty (higher=fewer chord changes)", "0.05"))

    weights = Weights(
        w_chroma=float(_prompt("Weight chroma (lower for melody-only)", "0.25")),
        w_mel_hit=float(_prompt("Weight melody-hit reward", "0.95")),
        w_mel_miss=float(_prompt("Weight melody-miss penalty", "0.60")),
        w_complexity=float(_prompt("Complexity penalty (higher=fewer extended chords)", "0.18")),
    )

    harmony = HarmonyConfig(
        input_type=input_type,
        style=style,
        richness=richness,
        scope=scope,
        key_str=key_str,
        change_penalty=change_penalty,
        use_hpss=use_hpss,
        use_melody=use_melody,
    )

    if mode == "freeflow":
        seg_mode = _prompt("Segmentation: auto / onsets / fixed", "onsets" if input_type == "melody" else "auto").lower()
        if seg_mode not in ("auto", "onsets", "fixed"):
            seg_mode = "auto"

        fixed_seg_sec = float(_prompt("Chord rate: fixed window seconds (used for fixed/auto fallback)", "2.0"))
        min_seg_sec = float(_prompt("Minimum segment seconds (onsets/auto)", "0.8"))

        program = int(_prompt("MIDI program (0=piano)", "0"))
        velocity = int(_prompt("Chord velocity (1-127)", "72"))
        max_notes = int(_prompt("Max notes per chord voicing (3..5)", "5"))
        max_notes = max(3, min(5, max_notes))

        return RunConfig(
            mode="freeflow",
            audio_path=audio,
            out_midi=out_midi,
            out_json=out_json,
            harmony=harmony,
            weights=weights,
            segmentation=SegmentationConfig(mode=seg_mode, fixed_seg_sec=fixed_seg_sec, min_seg_sec=min_seg_sec),
            freeflow_midi=FreeflowMidiConfig(program=program, velocity=velocity, max_notes_per_chord=max_notes),
        )

    # TEMPO mode prompts
    bpm_s = _prompt("Tempo BPM (blank to auto-estimate)", "")
    bpm = float(bpm_s) if bpm_s.strip() else None

    ts = _prompt("Time signature (e.g., 4/4, 7/8)", "4/4")
    subdivision = _prompt("Grid subdivision: 1/8 or 1/16", "1/8")
    if subdivision not in ("1/8", "1/16"):
        subdivision = "1/8"

    chord_rate = _prompt("Chord change rate: 1_bar / 2_bars / 2_beats", "1_bar")
    if chord_rate not in ("1_bar", "2_bars", "2_beats"):
        chord_rate = "1_bar"

    groove = _prompt("Groove: pop / rock / funk / edm", "pop").lower()
    if groove not in ("pop", "rock", "funk", "edm"):
        groove = "pop"

    include_drums = _yesno("Include drums?", True)
    include_bass = _yesno("Include bass?", True)
    include_chords = _yesno("Include chords?", True)

    program_chords = int(_prompt("Chords program (0=piano)", "0"))
    program_bass = int(_prompt("Bass program (33=Acoustic Bass GM)", "33"))
    max_notes = int(_prompt("Max notes per chord (3..5)", "4"))
    max_notes = max(3, min(5, max_notes))

    return RunConfig(
        mode="tempo",
        audio_path=audio,
        out_midi=out_midi,
        out_json=out_json,
        harmony=harmony,
        weights=weights,
        tempo=TempoConfig(
            bpm=bpm,
            time_signature=ts,
            subdivision=subdivision,
            chord_rate=chord_rate,
            groove=groove,
            include_drums=include_drums,
            include_bass=include_bass,
            include_chords=include_chords,
        ),
        tempo_midi=TempoMidiConfig(
            program_chords=program_chords,
            program_bass=program_bass,
            max_notes_per_chord=max_notes,
        ),
    )
