import json
import os
import tempfile
from pathlib import Path

import streamlit as st

from freeflow_harmonizer.config import (
    RunConfig,
    HarmonyConfig,
    Weights,
    SegmentationConfig,
    FreeflowMidiConfig,
    TempoConfig,
    TempoMidiConfig,
)
from freeflow_harmonizer.pipeline import run


# -----------------------------
# UI Helpers
# -----------------------------
def save_uploaded_file(uploaded_file, dir_path: str) -> str:
    suffix = Path(uploaded_file.name).suffix or ".wav"
    out_path = os.path.join(dir_path, f"input{suffix}")
    with open(out_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return out_path


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clamp_int(x, lo, hi, default):
    try:
        v = int(x)
        return max(lo, min(hi, v))
    except Exception:
        return default


# -----------------------------
# Page
# -----------------------------
st.set_page_config(
    page_title="Backing Track Generator",
    page_icon="🎻",
    layout="wide",
)

st.title("🎻 Backing Track Generator")
st.caption("Two modes: **Freeflow (rubato, chords only)** and **Tempo (grid, chords+bass+drums)**")

colA, colB = st.columns([1.2, 1])

with colA:
    st.subheader("1) Upload audio")
    uploaded = st.file_uploader(
        "Upload a WAV/MP3/FLAC file",
        type=["wav", "mp3", "flac", "m4a", "aiff", "aif"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        st.audio(uploaded)

with colB:
    st.subheader("2) Choose mode")
    mode = st.radio(
        "Mode",
        ["freeflow", "tempo"],
        index=0,
        help="Freeflow = rubato, no tempo grid (chords only). Tempo = BPM/time-signature grid (chords+bass+drums).",
        horizontal=True,
    )

st.divider()

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.header("Settings")

# Shared harmony controls
st.sidebar.subheader("Harmony")
input_type = st.sidebar.selectbox("Input type", ["melody", "mixed"], index=0)
style = st.sidebar.selectbox("Style bias", ["film", "classical", "pop", "jazz"], index=0)
richness = st.sidebar.selectbox("Harmony richness", ["basic", "rich", "lush"], index=2)
scope = st.sidebar.selectbox("Chord root scope", ["diatonic", "all_roots"], index=0)
key_str = st.sidebar.text_input("Optional key (e.g., 'D min', 'Bb maj')", value="")
change_penalty = st.sidebar.slider("Chord change penalty", 0.0, 0.5, 0.05, 0.01)

use_hpss = st.sidebar.checkbox("Use HPSS (harmonic extraction)", value=True)
use_melody = st.sidebar.checkbox("Use melody conditioning (pyin)", value=(input_type == "melody"))

with st.sidebar.expander("Scoring weights (advanced)", expanded=False):
    w_chroma = st.slider("Weight: chroma match", 0.0, 1.5, 0.25, 0.05)
    w_mel_hit = st.slider("Weight: melody-hit reward", 0.0, 2.0, 0.95, 0.05)
    w_mel_miss = st.slider("Weight: melody-miss penalty", 0.0, 2.0, 0.60, 0.05)
    w_complexity = st.slider("Weight: complexity penalty", 0.0, 1.0, 0.18, 0.01)

weights = Weights(
    w_chroma=w_chroma,
    w_mel_hit=w_mel_hit,
    w_mel_miss=w_mel_miss,
    w_complexity=w_complexity,
)

harmony = HarmonyConfig(
    input_type=input_type,
    style=style,
    richness=richness,
    scope=scope,
    key_str=key_str,
    change_penalty=float(change_penalty),
    use_hpss=use_hpss,
    use_melody=use_melody,
)

# Mode-specific controls
if mode == "freeflow":
    st.sidebar.subheader("Freeflow mode")
    seg_mode = st.sidebar.selectbox("Segmentation", ["onsets", "auto", "fixed"], index=0)
    fixed_seg_sec = st.sidebar.slider("Fixed window seconds (fallback)", 0.5, 8.0, 2.0, 0.1)
    min_seg_sec = st.sidebar.slider("Min segment seconds", 0.2, 3.0, 0.8, 0.1)

    st.sidebar.subheader("MIDI (freeflow)")
    program = st.sidebar.number_input("Program (0=piano)", min_value=0, max_value=127, value=0)
    velocity = st.sidebar.slider("Chord velocity", 1, 127, 72, 1)
    max_notes = st.sidebar.slider("Chord voicing notes", 3, 5, 5, 1)

else:
    st.sidebar.subheader("Tempo mode")
    bpm_mode = st.sidebar.radio("Tempo source", ["Auto-estimate", "Manual"], index=0, horizontal=True)
    bpm = None
    if bpm_mode == "Manual":
        bpm = st.sidebar.number_input("BPM", min_value=30.0, max_value=240.0, value=120.0, step=1.0)

    time_sig = st.sidebar.text_input("Time signature (e.g., 4/4, 7/8)", value="4/4")
    subdivision = st.sidebar.selectbox("Grid subdivision", ["1/8", "1/16"], index=0)
    chord_rate = st.sidebar.selectbox("Chord rate", ["1_bar", "2_bars", "2_beats"], index=0)
    groove = st.sidebar.selectbox("Groove", ["pop", "rock", "funk", "edm"], index=0)

    include_chords = st.sidebar.checkbox("Include chords", value=True)
    include_bass = st.sidebar.checkbox("Include bass", value=True)
    include_drums = st.sidebar.checkbox("Include drums", value=True)

    st.sidebar.subheader("MIDI (tempo)")
    program_chords = st.sidebar.number_input("Chords program (0=piano)", min_value=0, max_value=127, value=0)
    program_bass = st.sidebar.number_input("Bass program (33=Acoustic Bass GM)", min_value=0, max_value=127, value=33)
    max_notes = st.sidebar.slider("Chord voicing notes", 3, 5, 4, 1)

    velocity_chords = st.sidebar.slider("Chords velocity", 1, 127, 70, 1)
    velocity_bass = st.sidebar.slider("Bass velocity", 1, 127, 78, 1)
    velocity_drums = st.sidebar.slider("Drums velocity", 1, 127, 90, 1)

# Output naming
st.sidebar.subheader("Output")
out_base = st.sidebar.text_input("Output name (base)", value="backing")
out_midi_name = f"{out_base}.mid"
out_json_name = f"{out_base}.json"


# -----------------------------
# Main action
# -----------------------------
generate = st.button("🚀 Generate Backing Track", type="primary", use_container_width=True)

if generate:
    if uploaded is None:
        st.error("Please upload an audio file first.")
        st.stop()

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = save_uploaded_file(uploaded, tmpdir)

        out_midi = os.path.join(tmpdir, out_midi_name)
        out_json = os.path.join(tmpdir, out_json_name)

        if mode == "freeflow":
            cfg = RunConfig(
                mode="freeflow",
                audio_path=audio_path,
                out_midi=out_midi,
                out_json=out_json,
                harmony=harmony,
                weights=weights,
                segmentation=SegmentationConfig(
                    mode=seg_mode,
                    fixed_seg_sec=float(fixed_seg_sec),
                    min_seg_sec=float(min_seg_sec),
                ),
                freeflow_midi=FreeflowMidiConfig(
                    program=int(program),
                    velocity=int(velocity),
                    max_notes_per_chord=int(max_notes),
                ),
            )
        else:
            cfg = RunConfig(
                mode="tempo",
                audio_path=audio_path,
                out_midi=out_midi,
                out_json=out_json,
                harmony=harmony,
                weights=weights,
                tempo=TempoConfig(
                    bpm=bpm,
                    time_signature=time_sig.strip(),
                    subdivision=subdivision,
                    chord_rate=chord_rate,
                    groove=groove,
                    include_chords=include_chords,
                    include_bass=include_bass,
                    include_drums=include_drums,
                ),
                tempo_midi=TempoMidiConfig(
                    program_chords=int(program_chords),
                    program_bass=int(program_bass),
                    max_notes_per_chord=int(max_notes),
                    velocity_chords=int(velocity_chords),
                    velocity_bass=int(velocity_bass),
                    velocity_drums=int(velocity_drums),
                ),
            )

        with st.spinner("Generating… (this can take a bit depending on audio length)"):
            try:
                run(cfg)
            except Exception as e:
                st.exception(e)
                st.stop()

        # Read outputs
        report = read_json(out_json)

        st.success("Done! Download your MIDI + report below.")

        # Preview summary
        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("Preview")
            st.json(
                {
                    "mode": report.get("mode"),
                    "duration_sec": report.get("duration_sec"),
                    "estimated_key": report.get("estimated_key"),
                    "bpm": report.get("bpm"),
                    "time_signature": report.get("time_signature"),
                    "subdivision": report.get("subdivision"),
                },
                expanded=False,
            )
        with right:
            st.subheader("Downloads")
            with open(out_midi, "rb") as f:
                st.download_button(
                    "⬇️ Download MIDI",
                    data=f,
                    file_name=out_midi_name,
                    mime="audio/midi",
                    use_container_width=True,
                )
            with open(out_json, "rb") as f:
                st.download_button(
                    "⬇️ Download JSON report",
                    data=f,
                    file_name=out_json_name,
                    mime="application/json",
                    use_container_width=True,
                )

        # Chord timeline
        st.subheader("Chord timeline")
        chords = report.get("segments") or report.get("chords") or []
        if chords:
            st.dataframe(chords, use_container_width=True, hide_index=True)
        else:
            st.info("No chord segments found in report (e.g., chords disabled in tempo mode).")

        # DAW guidance
        st.subheader("Ableton tips")
        if mode == "freeflow":
            st.markdown(
                """
- MIDI files are **silent** unless you load an **instrument** on the MIDI track (pad/piano/strings).
- **Freeflow** MIDI is aligned in **real seconds**. Line up the **start of audio** and **start of MIDI**.
- If your audio starts with silence, trim it or align the MIDI start accordingly.
"""
            )
        else:
            st.markdown(
                """
- MIDI files are **silent** unless you load instruments on the MIDI tracks.
- **Tempo** mode uses a BPM grid. For best alignment:
  - set Ableton tempo to the **same BPM** used in the report, or
  - warp audio so bar 1 matches.
- Drums are written on **GM drum channel** (channel 10).
"""
            )
