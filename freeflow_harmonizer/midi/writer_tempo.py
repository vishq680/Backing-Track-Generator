from __future__ import annotations
from typing import List, Tuple
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

from ..config import TempoMidiConfig
from ..tempo.grid import TimeSignature
from ..harmony.voicing import voice_chord
from .types import TempoChordSegment


def seconds_to_ticks(sec: float, bpm: float, tpqn: int) -> int:
    # beats per second = bpm / 60
    # ticks per second = tpqn * bpm / 60
    return int(round(sec * tpqn * (bpm / 60.0)))


def write_backing_tempo(
    out_midi: str,
    bpm: float,
    ts: TimeSignature,
    chord_segments: List[TempoChordSegment],
    bass_events: List[Tuple[float, float, int, int]],
    drum_events: List[Tuple[float, float, int, int]],
    midi: TempoMidiConfig,
):
    mid = MidiFile(type=1, ticks_per_beat=midi.tpqn)

    meta = MidiTrack()
    tr_chords = MidiTrack()
    tr_bass = MidiTrack()
    tr_drums = MidiTrack()

    mid.tracks.append(meta)
    mid.tracks.append(tr_chords)
    mid.tracks.append(tr_bass)
    mid.tracks.append(tr_drums)

    meta.append(MetaMessage("track_name", name="TempoBacking", time=0))
    meta.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(float(bpm)), time=0))
    meta.append(MetaMessage("time_signature", numerator=ts.numerator, denominator=ts.denominator, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))

    # Chords
    tr_chords.append(MetaMessage("track_name", name="Chords", time=0))
    tr_chords.append(Message("program_change", channel=midi.channel_chords, program=int(midi.program_chords), time=0))

    # Bass
    tr_bass.append(MetaMessage("track_name", name="Bass", time=0))
    tr_bass.append(Message("program_change", channel=midi.channel_bass, program=int(midi.program_bass), time=0))

    # Drums
    tr_drums.append(MetaMessage("track_name", name="Drums", time=0))

    # Collect absolute-tick events
    chord_events = []
    for seg in chord_segments:
        t0 = seconds_to_ticks(seg.start, bpm, midi.tpqn)
        t1 = seconds_to_ticks(seg.end, bpm, midi.tpqn)
        if t1 <= t0:
            continue
        # No melody center in tempo mode; choose a fixed top constraint
        voiced = voice_chord(seg.pcs, melody_center_midi=76, max_notes=midi.max_notes_per_chord)
        for n in voiced:
            chord_events.append((t0, Message("note_on", channel=midi.channel_chords, note=int(n), velocity=int(midi.velocity_chords), time=0)))
            chord_events.append((t1, Message("note_off", channel=midi.channel_chords, note=int(n), velocity=0, time=0)))

    bass_msg = []
    for (s0, s1, note, vel) in bass_events:
        t0 = seconds_to_ticks(s0, bpm, midi.tpqn)
        t1 = seconds_to_ticks(s1, bpm, midi.tpqn)
        if t1 <= t0:
            continue
        bass_msg.append((t0, Message("note_on", channel=midi.channel_bass, note=int(note), velocity=int(vel), time=0)))
        bass_msg.append((t1, Message("note_off", channel=midi.channel_bass, note=int(note), velocity=0, time=0)))

    drum_msg = []
    for (s0, s1, note, vel) in drum_events:
        t0 = seconds_to_ticks(s0, bpm, midi.tpqn)
        t1 = seconds_to_ticks(s1, bpm, midi.tpqn)
        if t1 <= t0:
            continue
        drum_msg.append((t0, Message("note_on", channel=midi.channel_drums, note=int(note), velocity=int(vel), time=0)))
        drum_msg.append((t1, Message("note_off", channel=midi.channel_drums, note=int(note), velocity=0, time=0)))

    def write_track(track: MidiTrack, events):
        events.sort(key=lambda x: x[0])
        last = 0
        for t, msg in events:
            msg.time = max(0, int(t - last))
            track.append(msg)
            last = t
        track.append(MetaMessage("end_of_track", time=1))

    write_track(tr_chords, chord_events)
    write_track(tr_bass, bass_msg)
    write_track(tr_drums, drum_msg)

    mid.save(out_midi)
