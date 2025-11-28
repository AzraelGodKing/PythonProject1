# Tic-Tac-Toe (CLI & GUI)

Terminal and Tkinter tic-tac-toe where you play as X against several AI personalities. Scores persist across runs, and the GUI remembers your toggle settings between sessions.

## Features
- Three difficulties (Easy random, Normal with personalities, Hard minimax) plus Normal personalities: balanced, defensive, aggressive, misdirection, mirror.
- CLI play with hints, persistent scoreboard, session history logging, and input via row/col or single digits.
- GUI with styled board, status/score panels, undo/hint buttons, theme/font toggles (high contrast, larger fonts), and persistent toggle settings.
- Scoreboard tamper detection and automatic recovery from the last valid snapshot.

## Run
- CLI: `py -3 tic-tac-toe.py`
- GUI: `py -3 gui.py`

## Tests
Run the test suite (CLI and GUI smoke): `py -3 -m unittest -q`

## Notes
- GUI toggle settings persist in `gui_settings.json` in the project root.
- Session history logs rotate with timestamps when saving from the CLI; the GUI exposes history viewing/saving.***
