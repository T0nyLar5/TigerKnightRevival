# notes/ index: which doc to read

Start with `AGENT_GUIDE.md`. For battle work, then read `battle_state.md`. Each area folder has a `README.md` guide (`lobby\`, `battle\`, `re\`, `research\`); open the topic files only for the detail you need. Paths are relative to `notes\`.

## Start here
- `AGENT_GUIDE.md`: hard rules, lobby and battle facts. Read first.
- `battle_state.md`: condensed current battle state (V37 = working base, walk helper, open issues). Read before any battle work.
- `HISTORY.md`: project timeline (problem -> solution, commit) and open problems. Read to learn what was tried.
- `reports/`: full subagent findings, one file per task (newest name = latest).
- `../tools/battle_timeline.py [log] [--from S --to S --only 0x2754 --max-lines 60]`: per-second battle log timeline. Use instead of raw logs.

## reports\ 11-07 and 11-08 (not listed above; newest last)
- `reports/20261107_0100_sync_velocity_static.md`: SyncVelocity/SyncAccelerate and ground-walk static study (inspector opt 6). Read when the hero's velocity or acceleration stays zero.
- `reports/20261107_0230_battle_state_archive_8b_10.md`: old battle_state sections 8b and 10 (walk variants 17-28, V29 plan). Read when you need old variant detail.
- `reports/20261107_0230_pinned_position_lockstep.md`: lockstep hypothesis for the pinned hero position, V33-36, inspector opt 7. Read when the position is pinned or does not move.
- `reports/20261107_0400_ground_speed_multiplier_hunt.md`: hunt for a zero ground-speed multiplier (none found; inspector opt 10). Read before hunting speed multipliers.
- `reports/20261107_0500_server_location_pullback.md`: whether LastValidServerLocation pulls the hero back (inspector opt B). Read when the hero snaps back to the server location.
- `reports/20261107_0600_syncunit_scan.md`: memory scan for the sync-unit vec3 (key C, not run in game). Read when scanning sync-unit memory.
- `reports/20261107_0700_stuck_sync_drive.md`: key D drives stuck sync copies; bSlowMove_DTS static. Read when testing key D or the slow-move flag.
- `reports/20261107_0800_root_motion.md`: root motion and animation state check (key E). Read when ruling out root motion as the movement driver.
- `reports/20261107_0900_challenge_control_gate.md`: challenge and control gate study (H1-H3, key F). Read when walking is blocked by challenge or control state.
- `reports/20261107_1000_person_max_speed_factor.md`: fPersonToSelf/HorseMaxSpeedFactor = 0 in the live game (key F). Read when a speed factor reads 0.
- `reports/20261107_1200_movement_presets.md`: movement presets (key I) and the V37 check. Read when choosing a movement preset to test.
- `reports/20261107_2200_pullback_echo.md`: pull-back after V37 and server echo V38/V39. Read when the hero is pulled back after walking.
- `reports/20261108_0000_character_creation.md`: character creation page in the fake lobby (how the client decides, TUTORIAL flag). Read when the character creation page is in question.
- `reports/20261108_0000_sync_position_feed.md`: V38/V39 logs and the V41/V42 position feed (failed). Read when testing a position echo to the client.
- `reports/20261108_0100_character_creation_finish.md`: character creation hangs on "loading role resources"; appearance not saved. Read when character creation hangs or the appearance is lost.
- `reports/20261108_0100_v41_log_check.md`: V41/V42 log check and framing. Read when reviewing V41/V42 frames.
- `reports/20261108_0200_snapback_writers.md`: Win64 decompile of the Location writers (snap-back teleport code). Read when working on the snap-back or the sync object.
- `reports/20261108_0040_training_interactions.md`: client msgs on the training ground (0x2750 ReqTutorialStep, 0x2774 ContinusCut), CmdSyncTutorialStage 0x4e93 decode, variant 43. Read when NPC/posts/challenge flow is in question.
- `reports/20261108_0300_appearance_all_items.md`: appearance not applied (cause) and all items in the warehouse. Read when the appearance or warehouse items are wrong.
- `reports/20261108_0300_walk_helper.md`: walk helper (`走路輔助.bat`) and the setter-caller investigation. Read when changing the walk helper or the ForceUpdatePlayerHumanLocation fix.

## lobby\ (guide: `lobby/README.md`)
- `lobby/login_flow.md` (table of contents): `login_flow_auth_entry.md` (sources, KEY FACT, auth, entry), `login_flow_data_loading.md` (data loading routes), `login_flow_init_and_push.md` (23-step init chain 3b, push routes).
- `lobby/state_and_actions.md`: unlock-all state (unlock_all.py), push-delivered rows, help panels, max level, soldier-tree freeze fix, known route gaps.
- `route_table.txt`: index of the 244 lobby routes (route index = response switch case). Read when looking up a route number.
- `client_log_first_login.txt`: raw client log from the first login (2026-11-04). Evidence only, never whole.
- `crash/analysis.md`: analysis of the 2026-11-04 client crash. `crash/`: dumps and logs (`*.dmp` gitignored). Read only the file a crash analysis names.
- Stubs only (old names, the content moved to the folders below): `lobby_protocol.md`.

## battle\ (guide: `battle/README.md`)
- `battle/launch_flow.md` (table of contents): `launch_flow_cmdline.md` (gameStartup, UE3 command line, game classes), `launch_flow_hosting.md` (battle protocol, hosting verdict, open leads), `launch_flow_lobby_trigger.md` (ParentWnd check, TCP option, map ids).
- `battle/sync_protocol.md` (table of contents): `sync_protocol_step1_wire.md` (wire format, MsgConnect), `sync_protocol_messages.md` (server<->client message tables), `sync_protocol_frames_replies.md` (frame cadence, reply sequence), `sync_protocol_step3_spawn.md` (AddPlayer, BattleStart, spawn notes).
- `battle/msg_dictionary.md`: one table of every battle message id (name, direction, body, effect, verified/hypothesis). Read first when a message id is in question.
- `battle/variants_and_tests.md`: variant N history, the 2026-11-05 PM correction, real test results for variants 15-16 onward. Read when choosing the next variant or reading a test result.
- `battle/movement_params.md`: all movement-related params (hero, controller, game, GRI, DataSet 0x26/0x27, 1e-4 floors) with live/default values; read when choosing what to write or test for walking.
- `battle/user_slow_events.md`: the user's recollection of actions that slow movement (unverified leads). Read when looking for slow or speed flags.
- `battle/variants_7_9_recheck.md`: variant 5/6 re-check and variants 7-9 (hero spawn order, DataSet).
- `battle/results_open_questions_1105.md`: lobby result pushes (gameResultGlance/gameResult), other findings, ranked open questions.
- `battle/walk_gate_v27_mod.md` (table of contents), for the walking problem: `walk_gate_input.md` (code that zeroes movement input), `walk_gate_native_v27.md` (native findings, V27/V28/V29), `walk_gate_script_mod.md` (KingdomGame.u mod pipeline), `walk_gate_mod_first_test.md` (failed first test and fix), `walk_gate_clock_clue.md` (match clock 00:00 clue).
- `../tools/ue_inspect.py` (launcher `英雄速度檢查.bat` option 1/2; option 4 = watch while holding W, 5 = property list: reports/20261106_2345_ue_inspect_watch.md; 8 = collision check, 9 = lift experiment: reports/20261107_0300_collision_check_lift.md): finds the hero Pawn via GNames/GObjObjects at runtime and prints speed props + Cheat Engine addresses (reports/20261106_2300_ue_inspect.md). Read when testing the zero-speed hypothesis.
- `../tools/pawn_probe.py` (launcher `英雄速度檢查.bat`): run while standing in battle; reads hero Pawn GroundSpeed/AccelRate/JumpZ from game memory (Win64), optional fix-write. Read when testing the zero-speed hypothesis.
- Stubs only (old names): `battle_launch.md`, `walk_gate.md`, `research_free_1105.md` (they point to the files above and to research\).

## re\ (guide: `re/README.md`)
- `re/config_tables_1105.md`: config.cfg / config_client.cfg / terrain.cfg cracked (2026-11-05). Read when you need the config cipher or table layout.
- `re/kingdom_exe_findings.md`: Kingdom-Win32-Shipping.exe and SyncClient.dll findings, UE3 config .bin cipher (2026-11-05). Read when reversing the battle exe.
- `re/server_dat.md`: the Server.dat / langandplatform.dat cipher, cracked. Read when touching server data files.
- `re/script_packages.md`: UE3 .u script package format and the decryptor (tools/updec.py, upatch.py). Read before patching a .u file.
- `re/ghidra_usage.md`: how to run tools/decompile.py (Ghidra headless, JDK 25). Read before a decompile.
- `decrypted/`: decrypted game configs (cfg tables, Server.dat, Silent.dat). Large; grep it, never read it whole.
- `map_ids.md`: mapId and gameMode mapping (17 = training ground, 11/12 tutorials). Read when a map or mode id is in question.

## research\ (guide: `research/README.md`)
- `research/research_input.md` (table of contents): `research_input_client_messages.md` (client->server Req types), `research_input_relay_and_battle_start.md` (relay rules, battle start/end), `research_input_battle_end_unknowns.md` (battle end, unknowns, test hints).
- `research/research_troops.md` (table of contents): `research_troops_creation.md` (0x4e23 soldier Ctl, DataSet), `research_troops_slave_addperson.md` (slave msg 3), `research_troops_plan.md` (minimum squad sequence), `research_troops_unknowns_update.md` (unknowns, function index, 2026-11-05 PM update).
- `research/research_ai.md`: SyncClient ai:: namespace, AI bot handling, slave AI messages. Read when working on enemy AI.
- `research/web_research.md`, `research/wayback_research.md`: web search and Wayback Machine research (background only). Read before repeating web searches.
- `scripts/`: decompiled Lua UI scripts (large data, grep only).
- Stubs only (old names): `research_input.md`, `research_troops.md`, `research_ai.md`, `web_research.md`, `wayback_research.md`, `server_dat.md`, `script_packages.md`, `ghidra_usage.md`.

## Owner guides (Traditional Chinese)
- `使用說明_假伺服器.md`: how to run the fake lobby (3_啟動假伺服器.bat).
- `使用說明_戰鬥測試.md`: how to run the battle test (6_啟動戰鬥伺服器.bat).
- `使用說明_外包AI.md`: how to use tools\ask_llm.py for bulk text work.
- `使用說明_CE追蹤.md` (copy server/text/ce_trace_guide.txt): how to use Cheat Engine + key H of 英雄速度檢查.bat to find the native code writing hero Location/Velocity (dynamic trace; reports/20261107_1100_dynamic_trace_prep.md has the module+offset -> Ghidra recipe).

## Repo root
- `../走路輔助.bat`: walk helper (`ue_inspect --walkhelper`). Start it after the hero appears (admin auto). Read when walking stops or the hero is pulled back.
- `../英雄速度檢查.bat`: live inspector, keys 1-9 A-J. Read when you need a live memory readout or a test key.
- `../一鍵測試_捏角色.bat`: character creation mode (fake lobby). Read when testing the character creation page.
- `../README.md`: one-paragraph project summary.
- `../tools/` and `../server/` have their own code; `AGENT_GUIDE.md` lists the tools.
- `re\protocol_catalog.md`: read when you need the full list of all 480 battle message ids (name, direction, category, handled/seen counts); regenerate with `tools\msg_catalog_build.py` (names from RTTI, ~40 unresolved).
