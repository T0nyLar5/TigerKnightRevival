# Battle msg dictionary + timeline tool (2026-11-06)
- notes/battle/msg_dictionary.md: ~75 lines, all top-level and slave messages, V/H status, sources.
- tools/battle_timeline.py: parses battleserver_*.log (RECV/SEND lines, frame inner=[..]); time zero = "TCP CONNECT". Name map is the NAMES dict in the script. Tested on logs 231519, 231417, 231254, 213957 (the tiny ones have no connect, empty output).
- Finding: logs 231519 (t=12-13 s, ~100/s) and 213957 show 0x2721/2737/2738 ReqMove flowing, i.e. the client did send walk input in those runs; battle_state.md says "cannot walk". Worth checking what the user saw in 231519.
- Nothing started; no server code touched.
