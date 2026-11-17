# Battle guide (SyncClient, lockstep frames, walking)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

This folder covers the battle path: how the lobby starts `frontend.exe` and the UE3 battle exe, the SyncClient wire protocol that `server\battle_server.py` must speak, the message tables, and the research on walking, troops, AI and battle end. Read `..\battle_state.md` first for the current state; it is the condensed summary.

Which file to read for which question:
- `..\battle_state.md`: current status, variant results (V1-V29), open questions. Read before any battle work.
- `msg_dictionary.md`: every battle message id (name, direction, body, effect, verified or hypothesis). Read first when a message id is in question.
- `launch_flow.md`: table of contents. `launch_flow_cmdline.md` (gameStartup, command line, game classes), `launch_flow_hosting.md` (battle protocol, results, hosting verdict), `launch_flow_lobby_trigger.md` (the ParentWnd check, the TCP option, map ids).
- `sync_protocol.md`: table of contents. `sync_protocol_step1_wire.md` (wire format, MsgConnect), `sync_protocol_messages.md` (message tables), `sync_protocol_frames_replies.md` (frame cadence, reply sequence), `sync_protocol_step3_spawn.md` (AddPlayer, BattleStart).
- `variants_and_tests.md`: read when choosing the next variant or reading a real test result.
- `variants_7_9_recheck.md`: read when touching hero spawn order or DataSet values.
- `results_open_questions_1105.md`: read for lobby result pushes (`gameResultGlance`, `gameResult`) and the ranked open-question list.
- `walk_gate_v27_mod.md`: table of contents for the walking problem. `walk_gate_input.md` (the code that zeroes movement input), `walk_gate_native_v27.md`, `walk_gate_script_mod.md`, `walk_gate_mod_first_test.md`, `walk_gate_clock_clue.md`.
- `..\research\research_input.md` and `..\research\research_troops.md`: input/relay rules and troop spawn research (static analysis).

Tags legend (used in all battle and re notes): [C] confirmed in code, [G] guess; H = read directly from code or data, M = inferred, L = guess. Addresses: `10xxxxxx` = Sync.dll / SyncClient.dll (Win32), `00xxxxxx` = Kingdom-Win32-Shipping.exe; frontend.exe VAs where stated.

Status: the hero spawns and the map loads; walking, troops, AI and battle results still do not work (see `..\battle_state.md`, section 1, for the newest variant).

## New topic notes (split 2026-11-08 from battle_state.md)
- `wire_and_messages.md` (wire format, message tables), `dataset_slots.md` (DataSet slots), `countdown_results.md` (countdown, battle start/end, results, configs), `walk_snapback.md` (speed factor, snap-back).
- Old full battle_state text: `../archive/battle_state_old.md`.
