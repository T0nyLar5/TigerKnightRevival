# Battle variants and real test results
> rev 6 | 2026-11-08 04:20 | V51 result (sprint+combo verified), V52 added
Summary: battle_server.py variant N history (step 4), the 2026-11-05 PM correction, and the step 6 real test results with variants 15-16.
Tags: see the legend in [README.md](README.md).
Source: notes/battle_launch.md 'Battle step 4', 'UPDATE 2026-11-05 PM', 'Battle step 6' (text moved unchanged, split 2026-11-06).

## Battle step 4 (variants; `battle_server.py --variant N`, launcher `一鍵測試_選版本.bat`, 2026-11-05)
New static findings (Win32 Sync.dll / SyncClient.dll, ~17 decompiles): (a) **0x4e20 CmdSync = varint + string(u16 len + bytes)** (not a vector; SyncClient 0x10060aa0 -> 0x1008be30); the client forwards it to slave vtable+0x50, which in `SyncSlave` (0x1012a154) is an empty function (0x10001010), so it only sets the client's "synced" flag [+0x98]; nothing reads that flag in the frame handler 0x100af840 (no gating found). (b) **Slave message 7 is header-only** (dispatcher 0x10034630 just calls callback vtable+4, reads no body); 9/0xd/0xc/0xe also bodyless/1 byte. (c) Msg 2 and 3 body = `uid uvar | kind svar | f0c uvar | f10 uvar | 6 x f16 (pos, dir) | uvar a | f16 b | uvar c` [H layout]; a feeds a unit-type lookup (slave-callback vtable+0x4c(a, kind), 2 only), b -> unit +0x7c, c -> +0x8c / player entry +0x24c. Troop type ids (a, kind) need the encrypted config tables, so we send 0. (d) NOT resolved statically: which Req the client sends after AddPlayer/BattleStart is decided on the UE3 side (Kingdom exe, not touched). Candidates by name in SyncClient: MsgReqSelectBornPos / SelectBornPosConfirm, MsgReqReBorn, MsgReqPlayerEvent, MsgReqTutorialStep. The log now tags every client message after the spawn as `RECV [after spawn]` and `summarize_logs.py` prints them, so tonight's run answers (d).
Variants (all log `VARIANT N` at start, every sent/received type, inner frame messages decoded):
- 0 = step 3 as before: AddPlayer + BattleStart in frames. Confidence it alone works: low-medium.
- 1 = Init(7) before AddPlayer. Cheap (bodyless); medium-low.
- 2 = CmdSync(0, empty) top-level right after ConnectAck, then step 3. Low (slave side is a no-op), but harmless.
- 3 = CmdSync + Init + AddPlayer + 3 x AddPerson (uid 20001-3, kind 0) + BattleStart. Medium-low; kind/type 0 for troops is a guess.
- 4 = like 3, one message per 10 frames (0.5 s) and BattleStart repeated after the loading sequence: tests a timing/ordering problem.
Order to try: **3 first** (superset: if anything spawns it shows), then **0**, then **1**, **2**, **4** only if 3 shows an odd result (e.g. crash/log difference). If 3 spawns the hero but crashes on troops, 1 is the next candidate. After each run: `tools\.venv\Scripts\python.exe -I tools\summarize_logs.py`.


## UPDATE 2026-11-05 PM (see notes/battle/variants_7_9_recheck.md)
Corrections to step 5: DataSet must have N >= 127 (UE3 reads index 0x7e; we sent 80), DataSet[2] is HEALTH (we sent 1), [0x18-0x1b] armor ids, [0x1e-0x21] weapon ids, position/direction are DataSet floats [9],[10] / [5..7]. Countdown is (1,3)(2,3..0)(3,0). Config tables are decrypted. Variants 7-9 implement this; recommended order 7, 8, 9, 5, 6.


## Battle step 6 (real test results 2026-11-05 evening + 0x2754 / 0x4e3e identified; variants 15, 16)
**Real tests (logs in `server\logs\`)**
| Variant | Log | Result |
|---|---|---|
| 10 (11-04 baseline) | `battleserver_20261105_180612.log` | Map OK, no hero. |
| 14 (10 + lone top-level 0x4e22 right after ConnectAck) | `battleserver_20261105_180920.log` | **HERO SPAWNS**, camera works, hero can't move or attack (attack may be the training stage's design). |
| 13 (10 + lone CmdSync) | `battleserver_20261105_181304.log` | Stuck on loading: **never send CmdSync**. |
| 11 | `battleserver_20261105_181540.log` | Like 14 plus a duplicate identical hero at the same spot (0x4e22 + ReBorn/slave AddPlayer both spawn). |
| 12 | `battleserver_20261105_181730.log` | Like 11, later crashes back to the lobby. |
So: **one top-level 0x4e22 (PlayerCtl with isSelf) is the whole spawn.** ReBorn and slave AddPlayer must NOT be sent (duplicate). "Defaults to party/team state" in 10/14 is a lobby matter.

**What the client sends after spawning (variant 14)** (registry `0x10093050` in Win32 SyncClient.dll: triples `push codec_factory | push reader | push type`; names resolved through the `sp_counted_impl_p<...>` RTTI that the reader constructs; script: temp `reg.py`, reproducible) [H]
- `0x2754` = **MsgReqPlayerBodyturn** (reader `0x100535b0`, writer `0x10053380`): `uvar uid | u8 a | u8 b | u8 c | 1-byte value | 1-byte value` (the last two are `FUN_10091cd0`/`10091ae0` u16 codecs, seen as single bytes `00 00`). Values change smoothly while the camera moves (`e8 19 f8`, `e2 1d f5` ...): it is the **camera/body-turn (yaw/pitch quantised) report every ~100 ms, NOT movement input.** Its codec is private: no Cmd shares it. The only turn Cmd, `0x4e24 MsgCmdBodyTurn`, is `uvar uid + 3 x f16` (shared with ReqBodyturnHighAccu 0x272c / ReqMove), a different layout, so there is no confident Req->Cmd mapping. Not echoed (own pawn already turns locally). Also existing: 0x272b MsgReqBodyturn, 0x2780 MsgReqSetSeekBodyTurn.
- `0x4e3e` = **MsgCmdPlayStateChange** (a Cmd type, but the client SENDS it): `uvar uid | u16 state (varint) | u8 bool`; seen `91 4e | 92 03 (=402) | 01` once, right after spawn. Neighbours: 0x4e3d MsgCmdAction, 0x4e3f MsgCmdEnergy. State 402 is probably "entered the playing state". Original master presumably broadcast it to all players, so variant 15/16 echo it verbatim top-level (M, cheap; could be harmless or ignored).
- `MsgMD5Check` (0x3ec) C->S: the client sends its two 32-hex file hashes (varint, str, str). Reply format unknown, nothing seen requiring one: **no reply** (L).
- **Why the hero can't move: most likely the "frozen" game state, not missing input relay.** Per research_free_1105 sec.2.6: countdown state 1 freezes, only `(2,0)` fires the unfreeze script events and BattleStart(slave 8) sets GameEngine flag 0x20000. Variant 14 ran the old countdown `(1,3)(2,3)(3,0)` without ever reaching `(2,0)` and without slave BattleStart. Also research_input.md: movement is client-authoritative, so no input echo should be needed; ReqMove (0x2721) never appeared because the pawn could not move.

**Variants (battle_server.py, selftest passes for 0-16)**
- **15** = 14 + relay: echo client 0x4e3e verbatim (top-level), decode/log 0x2754 (not echoed), no MD5Check reply, never CmdSync. Every relay is logged `SEND RELAY ...` / `RELAY-CANDIDATE`. Confidence it makes the hero move: low (20%).
- **16** = 15 + unfreeze: slave BattleStart(8) in a frame at +3 s and top-level countdown `(2,2)(2,1)(2,0)(3,0)` 1 s apart starting +3.2 s. Confidence: medium-low (40%): this is the code-backed unfreeze path.
- **Test order: 16 first** (superset of 15), then 15 if 16 behaves oddly (crash / duplicate hero). After each run: `tools\.venv\Scripts\python.exe -I tools\summarize_logs.py`; look for `RECV [after spawn]` 0x2721 MsgReqMove (= hero moving) and any new Req types.


## V44-V46 (2026-11-08, UNTESTED): troops and enemy AI on the V37 walk base
V44 = V37 + 3 own troops at +12 s; V45 = V44 + AI enemy hero at +16 s (camp 0, 0x4e4a); V46 = V45 + 3 enemy troops at +20 s. Use map 3. Details: reports/20261108_0400_troops_ai_variants.md.

V44 result (owner, 02:00): hero fine, troops/AI messages sent correctly, NO troops (mode 5 KingdomChallengeGame, map 3). The vs-computer run (mode 2) had no battle server, so it is untested. See reports/20261108_0215_v44_troops_check.md.

## V47/V48 (2026-11-08, UNTESTED) spawn + owner gear
V47 = V44 + slave AddPlayer pos = map spawn (V37 sent 0,0,0 -> hero at (325,326) top-right on map 3) + hero gear from last_prebattle.json / player.json. V48 = V47 + face bytes + 0x4c banner (guesses). Env TK_SPAWN="x,y,z" overrides spawn. Test: map 3, vs-computer, variant 47; check first 0x2737 in the log and whether troops stand near the hero. Report: reports/20261108_0450_battle_spawn_troops_gear.md.


## V47 owner test + V49/V50/V51 (2026-11-08, UNTESTED)
V47 owner result (map 3, mode 2): spawn fixed (first 0x2737 = Camp1Pos), no troops, no combo, no sprint, no weapon switch, no voice. Pattern check + decoded Cmd layouts: reports/20261108_0320_v47_followup.md.
- V49 = V47 + one enemy AI general at +22 s, 20 m in +x (TK_ENEMY_DIST). Tests: does an enemy make the battle "real" (troops, combo)?
- V50 = V47 + replies 0x2774 -> Cmd 0x4ed5 (combo) and 0x273e -> Cmd 0x4e55 (sprint); field values partly guessed. TK_V50_EXTRA=block,swing,weapon adds more pairs (weapon-switch key is probably 0x272d -> 0x4e25, fields unknown).
- V51 = V49 + V50.
- V47+ hero HP = 300 (sex 0) / 280 (sex 1) from unit_default.ini [player]; env TK_HP overrides. Order: V47, V49, V50, V51.- V51 owner result: sprint + combo VERIFIED working; weapon switch, sprint attack, troops, enemy, voice not.
- V52 = V51 + army id from last_prebattle.json (default 112014, TK_ARMY) in [0x3e]/troop slots, hero/enemy [0x44],[0x49],[0x4a]=0, enemy [0x26]/[0x27]=1.0. Lobby 2-star fix. Report 20261108_0420_v51_scoreboard. Untested.
