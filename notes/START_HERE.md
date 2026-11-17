# START HERE (read only this, then only the notes your task needs)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

## What the project is
Tiger Knight (Steam 415660) is shut down. This repo (`<REPO>`) revives it for the owner's solo play: a fake Pomelo lobby (`server\lobby.py`, ports 3010-3019) and a fake battle server (`server\battle_server.py`, TCP 7777) talk to the client. The owner is not a programmer: user-facing text is simple Traditional Chinese. The game dir is read-only.

## Current state (2026-11-08)
1. Lobby login, entry and init chain work. Character creation works and the name saves; the 3D appearance fix is untested.
2. Battle: the hero walks freely for the whole battle with `走路輔助.bat`. Working base = V37 (DataSet 0x26/0x27 = 1.0).
3. Open: sprint (double W) unanswered; snap-back masked by the walk helper (no server fix); training-ground NPC/post interactions odd (V43 untested); troops, AI, battle end and results untested.
4. Older open: HUD timer 00:00; map 11 spawn under the map (not started); 1440p resolution (on hold).

## Rules for agents (full: `AGENT_GUIDE.md`)
- Python only as `tools\.venv\Scripts\python.exe -I`. Never run game exes or write to the game dir.
- .bat files: pure ASCII with CRLF. Chinese text goes in `server\text\*.txt`.
- Never read a whole file over ~200 lines or a whole log. Never dump `server\data\player.json`, cfg tables, Ghidra output or `re\protocol_catalog.md`.
- Never write the Steam ticket (`psw`) anywhere. Back up `player.json` before changing it.
- Never send CmdSync (0x4e20): it sticks the loading screen.
- Before finishing: stop your processes; nothing may listen on 3010-3019 or 7777.
- Mark claims **verified** (real test or log) or **hypothesis** (static).
- Each note's line 2 is a stamp: `> rev N | YYYY-MM-DD HH:MM | <one-line summary of the last change>`. When you edit a note, bump N and replace the line (keep ONE line only; full history = `git log <file>`). Read the stamp first to judge if a note is current.
- After a milestone: 1-3 lines at the end of `HISTORY.md`. Full findings: `reports\YYYYMMDD_HHMM_<topic>.md`.

## Which note for which task
| Task | Read |
|---|---|
| Walking, snap-back, walk helper | `battle_state.md`, `battle/walk_snapback.md`, `battle/walk_gate_input.md` |
| Next variant, a test result | `battle/variants_and_tests.md`, `battle/movement_params.md` |
| A battle message id | `battle/msg_dictionary.md`; grep `re/protocol_catalog.md` |
| Wire format, frames | `battle/wire_and_messages.md`, `battle/sync_protocol.md` |
| DataSet slot meaning | `battle/dataset_slots.md` |
| Countdown, battle end, results | `battle/countdown_results.md`, `battle/results_open_questions_1105.md` |
| Launch path, map ids | `battle/launch_flow.md`, `map_ids.md` |
| Lobby login, route, init stall | `lobby/README.md`, then `lobby/login_flow.md` and its parts |
| Lobby client crash | `crash/analysis.md` |
| Ciphers, `.u` patching, Ghidra | `re/README.md`, then the file it names |
| Enemy AI, troops | `research/README.md`, then the file it names |
| Tools, launchers | `tools_map.md` |
| Chinese owner guides | `使用說明_*.md` |
| One past task's evidence | `INDEX.md` (reports list) |
| Timeline | `HISTORY.md` (tail only) |
