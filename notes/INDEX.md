# notes/ index (condensed 2026-11-08; old full version: archive/INDEX_old.md)
> rev 2 | 2026-11-08 02:06 | folder tidy: moved old logs and tools\work scratch to _待刪除 (see reports\20261108_0205_folder_tidy.md)

Start with `START_HERE.md`. Paths are relative to `notes\` unless they start with `..\` (repo root) or `tools\`/`server\`.

## Top-level notes
- `START_HERE.md`: project, state, rules, task table. Read first.
- `AGENT_GUIDE.md`: hard rules (condensed). Lobby and battle facts in short form.
- `tools_map.md`: all tools, launchers and env vars (split from the old guide).
- `battle_state.md`: current battle state (V37 working base, walk helper, open issues). Short; points to topic notes.
- `HISTORY.md`: condensed timeline + last 30 entries verbatim. Full old text: `archive/HISTORY_old.md`.
- `map_ids.md`: mapId / gameMode table (17 = training ground).
- `route_table.txt`: index of the 244 lobby routes (route number = response switch case; used by `tools\schema.py`).
- `client_log_first_login.txt` (evidence only, never read whole), `crash/` (dumps `*.dmp` gitignored; `analysis.md` = client crash).
- `archive/`: full pre-split text: `HISTORY_old.md`, `AGENT_GUIDE_old.md`, `INDEX_old.md`, `battle_state_old.md`.
- Old-name stubs (tiny, point to the split files): `battle_launch.md`, `walk_gate.md`, `research_free_1105.md`, `lobby_protocol.md`, `research_input.md`, `research_troops.md`, `research_ai.md`, `web_research.md`, `wayback_research.md`, `server_dat.md`, `script_packages.md`, `ghidra_usage.md`.
- Owner guides (Chinese): `使用說明_假伺服器.md`, `使用說明_戰鬥測試.md`, `使用說明_外包AI.md` (`tools\ask_llm.py`), `使用說明_CE追蹤.md` (Cheat Engine trace, key H).

## lobby\ (guide: `lobby/README.md`)
- `lobby/login_flow.md` (contents) -> `login_flow_auth_entry.md`, `login_flow_data_loading.md`, `login_flow_init_and_push.md` (23-step init chain, 3b).
- `lobby/state_and_actions.md`: unlock-all state (`tools\unlock_all.py`), push rows, help panels, route gaps.

## battle\ (guide: `battle/README.md`)
- Launch: `battle/launch_flow.md` (contents) -> `launch_flow_cmdline.md`, `launch_flow_hosting.md`, `launch_flow_lobby_trigger.md`.
- Wire and messages: `battle/wire_and_messages.md` (new split), `battle/sync_protocol.md` (contents) -> `sync_protocol_step1_wire.md`, `sync_protocol_messages.md`, `sync_protocol_frames_replies.md`, `sync_protocol_step3_spawn.md`.
- `battle/msg_dictionary.md`: one table of battle message ids (verified / hypothesis).
- `battle/dataset_slots.md` (new split): DataSet u32 slot meanings.
- `battle/countdown_results.md` (new split): countdown, BattleStart/End, results pushes, config and key functions.
- Variants and tests: `battle/variants_and_tests.md`, `battle/variants_7_9_recheck.md`, `battle/results_open_questions_1105.md`, `battle/user_slow_events.md` (user's unverified leads).
- Movement: `battle/movement_params.md` (all move params, live/default values), `battle/walk_snapback.md` (new split: speed factor, snap-back).
- Walk gate: `battle/walk_gate_v27_mod.md` (contents) -> `walk_gate_input.md`, `walk_gate_native_v27.md`, `walk_gate_script_mod.md`, `walk_gate_mod_first_test.md`, `walk_gate_clock_clue.md`.
- Tools: `..\tools\ue_inspect.py` (launchers `英雄速度檢查.bat`, `走路輔助.bat`), `..\tools\pawn_probe.py`, `..\tools\battle_timeline.py` (per-second battle log view; use instead of raw logs), `..\tools\summarize_logs.py`.

## re\ (guide: `re/README.md`)
- `re/config_tables_1105.md`: config.cfg / config_client.cfg / terrain.cfg cipher and table layout.
- `re/kingdom_exe_findings.md`: Kingdom-Win32-Shipping.exe and SyncClient.dll findings; UE3 .bin cipher.
- `re/server_dat.md`: Server.dat / langandplatform.dat cipher (cracked).
- `re/script_packages.md`: UE3 .u package format and decryptor (`tools\updec.py`, `upatch.py`).
- `re/ghidra_usage.md`: running `tools\decompile.py` (Ghidra 12.2 headless, JDK 25).
- `re/protocol_catalog.md`: generated (`tools\msg_catalog_build.py`), 480 battle message ids. Do not hand-edit; grep it.
- `decrypted/`: decrypted configs (cfg tables, ue_config). Large; grep only. `scripts/`: decompiled Lua UI scripts. Large; grep only.

## research\ (guide: `research/README.md`)
- Input rules: `research/research_input.md` (contents) -> `research_input_client_messages.md`, `research_input_relay_and_battle_start.md`, `research_input_battle_end_unknowns.md`.
- Troops: `research/research_troops.md` (contents) -> `research_troops_creation.md`, `research_troops_slave_addperson.md`, `research_troops_plan.md`, `research_troops_unknowns_update.md`.
- `research/research_ai.md`: SyncClient `ai::` namespace and bot handling.
- `research/web_research.md`, `research/wayback_research.md`: background only; do not repeat these searches.

## reports\ (one file per task; newest = latest; evidence, not summaries)
- Walking and speed (11-06 to 11-07): `20261106_1900_walk_v28_script_mod_A`, `20261106_2130_spawn_points_v30`, `20261106_2300_ue_inspect`, `20261106_2345_ue_inspect_watch`, `20261107_0100_sync_velocity_static`, `20261107_0230_battle_state_archive_8b_10` (old variants V17-V36), `20261107_0230_pinned_position_lockstep`, `20261107_0300_collision_check_lift`, `20261107_0400_ground_speed_multiplier_hunt`, `20261107_0500_server_location_pullback`, `20261107_0600_syncunit_scan`, `20261107_0700_stuck_sync_drive`, `20261107_0800_root_motion`, `20261107_0900_challenge_control_gate`, `20261107_1000_person_max_speed_factor`, `20261107_1100_dynamic_trace_prep`, `20261107_1200_movement_presets`.
- Pull-back and position feed: `20261107_2200_pullback_echo`, `20261108_0000_sync_position_feed`, `20261108_0100_v41_log_check`, `20261108_0200_snapback_writers`, `20261108_0300_walk_helper`.
- Lobby and character: `20261108_0000_character_creation`, `20261108_0100_character_creation_finish`, `20261108_0300_appearance_all_items`.
- Training ground: `20261108_0040_training_interactions`.
- Message timeline: `20261106_1500_msg_dictionary_timeline`.
- Read the one report a task names, never the whole folder.

## Moved out of the repo (2026-11-08 reorg, not deleted)
- `..\_待刪除\` (gitignored, user may delete): `tools\ghidra_projects_d` (1 GB, unused), two 219 MB temp outputs in `tools\work\` (`upatch.py` regenerates them), 7 zero-reference scripts (`disstr`, `findcalls`, `funcstart`, `strpush`, `strs`, `tkstr`, `vaxref`), both `__pycache__` folders, and 117 old server logs (kept: newest 5 plus logs cited by notes).
- 2026-11-08 02:06 tidy (`reports\20261108_0205_folder_tidy.md`): `_待刪除\old_logs\` (15 server logs) and `_待刪除\tools_work_scratch\` (59 zero-reference items from `tools\work`).
