from __future__ import annotations
from typing import List
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

from ..config import FreeflowMidiConfig
from ..harmony.voicing import voice_chord
from .types import SegmentChord


def seconds_to_ticks_1ms(sec: float) -> int:
    return int(round(sec * 1000.0))


def write_chords_freeflow(out_midi: str, segments: List[SegmentChord], midi: FreeflowMidiConfig):
    mid = MidiFile(type=1, ticks_per_beat=midi.tpqn)
    meta = MidiTrack()
    tr = MidiTrack()
    mid.tracks.append(meta)
    mid.tracks.append(tr)

    meta.append(MetaMessage("track_name", name="FreeflowChordBacking", time=0))
    meta.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(midi.bpm), time=0))

    tr.append(MetaMessage("track_name", name="Chords", time=0))
    tr.append(Message("program_change", channel=midi.channel, program=int(midi.program), time=0))

    events = []
    for seg in segments:
        t0 = seconds_to_ticks_1ms(seg.start)
        t1 = seconds_to_ticks_1ms(seg.end)
        if t1 <= t0:
            continue
        mel_center = seg.melody_center if seg.melody_center is not None else 72
        voiced = voice_chord(seg.pcs, mel_center, midi.max_notes_per_chord)
        for n in voiced:
            events.append((t0, Message("note_on", channel=midi.channel, note=int(n), velocity=int(midi.velocity), time=0)))
            events.append((t1, Message("note_off", channel=midi.channel, note=int(n), velocity=0, time=0)))

    events.sort(key=lambda x: x[0])
    last = 0
    for t, msg in events:
        msg.time = max(0, int(t - last))
        tr.append(msg)
        last = t

    tr.append(MetaMessage("end_of_track", time=1))
    mid.save(out_midi)
