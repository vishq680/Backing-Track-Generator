# Backing Track Generator (Freeflow + Tempo)

Two modes:
1) FREEFLOW (rubato): chords-only, aligned to audio in real seconds (1 tick = 1ms)
2) TEMPO (grid): chords + bass + drums aligned to BPM/time signature

## Install
pip install -r requirements.txt

## Run (interactive)
cd SunoBacking
python -m freeflow_harmonizer.cli --interactive

## Ableton tips
- MIDI files are silent unless you load an instrument on the MIDI track.
- Freeflow mode: align audio start and MIDI start to same time; chord changes match audio seconds.
- Tempo mode: set Ableton tempo to the same BPM used (or imported), then align at bar 1.
