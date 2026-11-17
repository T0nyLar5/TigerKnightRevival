# ue_inspect options 4 (watch while holding W) and 5 (property list)
Status: offline selftest only (mock heap). NOT yet run in the real game. Layout guesses below are hypotheses until the first run.

## What was added (tools/ue_inspect.py, `--watch` / `--props`; bat menu 4 / 5)
- `Walker`: learns UStruct SuperField / Children / UField.Next offsets at runtime (scans class-object header 0x58..0x130; picks the SuperField offset whose chain reaches Object and Pawn, and the Children+Next pair giving the longest chain of properties owned by class Pawn). Then lists properties of a whole class chain with offsets (UProperty Offset +0x8c, already verified).
- State name: UObject.StateFrame assumed at obj+0x20 (UE3 layout: vtbl 0, HashNext 8, Flags 0x10, HashOuterNext 0x18, StateFrame 0x20, ... Outer 0x40 Name 0x48 Class 0x50 matches). FStateFrame {Node, StateNode}: scans frame +8/+0/+16 for a pointer whose class is `State`; also tries obj offsets 0x18/0x28/0x30. Prints "?" if none found.
- Option 4: header lines (state names, PlayerInput object, which input floats exist/missing, bIgnoreMove/LookInput, up to 15 bool/byte flags matching Move|Lock|Freeze|Stun|Ignore|Sync on controller+pawn), then 5 s countdown after Enter, then 33 rows (0.25 s, 8 s): aForward aStrafe aBaseY aBaseX aUp RawJoyUp RawJoyRight aMouseX, pawn Acceleration, Velocity, Physics; state changes appended to a row; flag changes summarized at the end. Saved to server\logs\pawn_probe_last.txt.
- Option 5: filter regex (default `Move|Accel|Speed|Phys|Lock|Sync`), name/type/offset/value, max 40 lines. BoolProperty is shown as the raw dword (bitmask not decoded; non-zero may mean set).
## Reading the result
- aForward/aBaseY non-zero while W held but Acceleration 0 -> pawn-side gate (state, flag). aForward stays 0 -> input never reaches PlayerInput (check controller state, bIgnoreMoveInput, key binding).
- Controller state not `PlayerWalking`/`Walking` (e.g. a spectate/cinematic state) is the likely blocker.
Selftest: `tools\.venv\Scripts\python.exe -I tools\ue_inspect.py --selftest`.
