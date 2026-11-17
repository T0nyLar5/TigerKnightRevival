# Battle message dictionary (2026-11-06)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
One table of every battle message known. Dir: C>S client->server, S>C server->client. Status: **V** = verified in a real test/log, **H** = hypothesis (static analysis / DLL layout, never seen, or effect not seen). Types: uvar = LEB128, svar = zigzag, f16 = half float, str = u16 len + bytes, vec = uvar count + items. Source tags: `bp` = server\battle_proto.py, `bs` = server\battle_server.py, `st` = notes\battle_state.md (section), `ri` = notes\research_input.md, `vt` = notes\battle\variants_and_tests.md. Sample logs: server\logs\battleserver_20261105_231519.log (newest), _213957 (many ReqMove). Names match tools\battle_timeline.py.
Frame: `u16 len(incl. header) | u16 type | body`, LE, XOR keystream per direction (st s2).

## Top-level messages
| id | name | dir | body | what it does / effect seen | status | source |
|---|---|---|---|---|---|---|
| 0x3e9 | MsgConnect | C>S | u32 1, u32 playerId, u32 1, u32 token | first message; log: playerId=10001 token=12345 | V | bp:13 |
| 0x3ea | MsgConnectAck | S>C | uvar code (0) | reply to Connect; client proceeds to load | V | bp:14 |
| 0x3eb | MsgPing | S>C, client echoes | uvar a, uvar b | sent once after Ack; client answers ~5 s later | V | bp:15, log 231519 |
| 0x3ec | MsgMD5Check | C>S seen | uvar, str, str | DLL says S>C, but client sends one after spawn; ignored | V (client sends) | bp:16, st s3 |
| 0x3ed 3ee 3ef 3f0 3f5 | InitiativeQuit, PingVal, ReqPause, CheckTime, LoadPlayerCache | ? | PingVal: uvar playerId, uvar ping | names only, never seen | H | bp:39-41 |
| 0x3f4 | MsgClientSystemInfo | C>S | uvar 0, str " [Win64]" | right after Connect | V | bp:18 |
| 0x2712-0x2714 | SplitPkg, SplitCompressPackage, Package | ? | | names only | H | bp:41 |
| 0x2715 | MsgFramework | S>C | uvar f1, uvar frameNo (from 1), u8 flag (2 = fragment), str payload = inner `u16 len\|u16 type\|body` slave msgs | carrier of slave msgs; every 50 ms even if empty | V | bp:19, st s2 |
| 0x279c | MsgReqSelfPing | C>S | uvar, uvar | every 5 s; needs no reply | V | bp:22 |
| 0x2721 | MsgReqMove | C>S | uvar uid, f16 x, y, z (V37 log: y always 0, x/z swing +-4 = velocity-like, NOT a position; position is 0x2737) | sent while hero walks (~100/s in 231519 t=13 s; ~139/s in 213957). Do NOT echo: echo as Cmd broke jumping (V23) | V (seen) | st s8b, ri:30 |
| 0x2722 | Req2722 | C>S | uvar uid, 2 bytes | seen with walking; meaning unknown | V seen, meaning ? | log 231519 t=13 s |
| 0x2737 | MsgReqPosition | C>S | uvar uid, f32 x, y, z | seen with walking and jump | V (seen) | st s8b |
| 0x2738 | MsgReqMoveActionStart | C>S | uvar uid, uvar mode (1/2), f16 x3 velocity | move starts | V (seen) | st s8b |
| 0x2739 | MsgReqMoveActionEnd | C>S | uvar uid, uvar mode | move/jump ends | V (seen) | st s8b |
| 0x2735, 0x2736, 0x273a | Req2735/36/3a | C>S | uid + 0-1 byte (2735: 2,4; 273a: 0/1) | seen in logs (attack/block/jump?) | V seen, meaning H | server\logs grep |
| 0x272f, 0x2732, 0x275e, 0x2778 | Req272f/2732/275e/2778 | C>S | uid + 0-4 bytes | rare after spawn (272f, 2732 at spawn +1 s); unknown | V seen, meaning ? | log 231519 |
| 0x2754 | MsgReqPlayerBodyturn | C>S | uvar uid, u8 a, u8 b, u8 c, 2 small codes | mouse/camera turn ~10/s; no answer needed | V seen, meaning M | bp:20, vt:33 |
| 0x2717, 0x2723/4 | ReqAction, Shot/ContinueShot | C>S | codecs shared with Cmd moves | names only | H | st s3 |
| 0x2770 | ReqTroopMove | C>S | | would be echoed as Cmd 0x4ece | H | st s3 |
| 0x274d | ReqReBorn | C>S | | answer with 0x4e80 | H | st s3 |
| 0x2792, 0x2796 | ReqSelectBornPos / Confirm | C>S | | only after CmdShowBornPos 0x4f03; answer 0x4f04/0x4f06 | H | ri:22,35 |
| 0x4e20 | MsgCmdSync | S>C | uvar, str | sets client synced flag. **NEVER send: stuck loading (V13)** | V (harmful) | bp:31, st s1 |
| 0x4e21, 0x4e24, 0x4e93 | CmdTerrainType, CmdBodyTurn, CmdSyncTutorialStage | S>C | | names only | H | bp:43-44 |
| 0x4e22 | MsgCmdAddPlayer | S>C | uvar uid, u8 isSelf, svar ptype (0 normal, 1 pending, 2 watcher), str name, uvar, uvar, str sname, uvar x4, vec<u8> face, uvar N + N*u32 DataSet (N=132), str | creates PlayerCtl; sent right after Ack; same uid twice = "Player Has Exist" | V (hero), H (enemy) | bp:32,207, st s3-4 |
| 0x4e23 | MsgCmdAddCreature | S>C | uvar uid, uvar N, N*u32 DataSet | creates SoldierCtl; DataSet[1]: 1 soldier/2 horse/4 boss; [0x32] owner must be a live PlayerCtl | H (V29 untested) | bp:294, st s10 |
| 0x4e3e | MsgCmdPlayStateChange | C>S (server echoes verbatim in best base) | uvar uid, uvar state, u8 bool; e.g. `91 4e 92 03 01` | client sends after spawn | V seen/echoed, meaning ? | bp:21, log 231519 t=2 s |
| 0x4e4a | MsgCmdControlAiPlayer | S>C | uvar uid | client runs AI of that PlayerCtl | H (V29 untested) | bp:295, st s3 |
| 0x4e50 | CmdMoveActionStart | S>C | = 0x2738 body | client DOES apply it to local pawn (echo killed jump, V23); V26 sends it | V effect, H use | st s8b, ri:30 |
| 0x4e51 | CmdMoveActionEnd | S>C | = 0x2739 body | V25 sends at +8 s: no walk effect | V (no fix) | st s8b |
| 0x4eca | CmdGhostPosition | S>C | uvar uid, f16 x,y,z (handler SyncClient 0x100a4370 -> sink vtable+0x40, vec3 only) | V23 echoed 0x2721 (y=0) -> broke jump; V38 sends the 0x2737 position instead | H (V38 untested) | reports/20261107_2200 |
| 0x273e, 0x2778 | Req (uid) / (uid, uvar) | C>S | seen on double-tap W (sprint attempt?), no reply known | V seen, meaning H | log 214643 |
| 0x4ece | CmdTroopMove | S>C | | answer to 0x2770 | H | st s3 |
| 0x4e73 | MsgCmdMatchEnd | S>C | one uvar (0/1; guess = result) | match end; V29 sends (1) at +150 s with slave 9 | H | ri:53, st s10 |
| 0x4e80 | MsgCmdReBorn | S>C | uvar uid, uvar N, N*u32 DataSet, str name, vec<u8> | needs PlayerCtl; calls UE3 spawn: **hero pawn appears** | V | bp:33,216 |
| 0x4e91 | MsgCmdUserLoadingFinish | S>C | uvar f1, uvar n, n * str | loading user list ('tiger'); sent with LoadingComplete | V | bp:34 |
| 0x4e92 | MsgCmdLoadingComplete | S>C | uvar | leaves the loading screen | V | bp:35 |
| 0x4e96 | MsgCmdCountDownUpdate | S>C | uvar f1, uvar state, uvar value | 1 = prepare/freeze, 2 = tick (value = s left, 0 = unfreeze), 3 = running. HUD+sound appear (V27/28) | V effect, H semantics | bp:36, st s5 |
| 0x4f03, 0x4f04, 0x4f06 | CmdShowBornPos / SelectBornPos / Confirm | S>C | | born position pick | H | ri:22 |
| 0x4ebc, 0x4f0a?, 0x4f2d | ChallengeMatchResult, InnerMatchEnd, BattleRoyaleEnd | S>C | | other end-of-match Cmds in the registry | H | ri:53 |

## Slave messages (inside MsgFramework payload; dispatcher Sync.dll 0x10034630)
| id | name | dir | body | effect | status | source |
|---|---|---|---|---|---|---|
| 1 | SlaveAddPlayer | S>C | uvar uid, svar kind, uvar f0c, uvar f10 (camp), f16 pos x3, f16 dir x3, f16, bool | player unit; needs top-level 0x4e22 first; V18+ sends for hero (pos 0) | V (hero) | bp:26,181, st s8b |
| 2 | SlaveAddCreature (horse) | S>C | as 3 | not sent | H | bp:28 |
| 3 | SlaveAddPerson (soldier) | S>C | uid, svar kind, f0c, f10 camp, pos x3, dir x3, uvar a (agentType key, agentparam.txt), f16 b, uvar c | missing key = NULL crash; V29 only | H | st s3, bp:182 |
| 4 | SlaveAddBullet | S>C | uid, kind, 6 f16 | | H | st s3 |
| 7 | SlaveInit | S>C | header only | callback +4; V18+ sends before AddPlayer | V (accepted) | bp:29 |
| 8 | SlaveBattleStart | S>C | header only | UE3 OnBattleStart (flag 0x20000 + script events); V27/28 at +8 s: HUD/sound, no walking change | V partial | bp:30, st s9 |
| 9 | SlaveBattleEnd | S>C | header only | SyncClient +0x228=1; UE3 reaction unknown; V29 at +150 s | H | st s5 |

## Notes
- Open: what gates walking (st s9). Logs 231519 and 213957 show 0x2721/2737/2738 flowing, so check what the hero actually did in those runs before trusting "cannot walk".
- DataSet index meanings: st section 4.
