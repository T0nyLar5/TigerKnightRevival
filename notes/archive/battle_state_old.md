# Battle server: current state (2026-11-08; working base = V37)
Deep detail: notes\battle\ and notes\re\ (map in notes\INDEX.md). Old walk variants V17-V36 and their dead ends: reports/20261107_0230_battle_state_archive_8b_10.md.
Addresses: `10xxxxxx` = SyncClient.dll / Sync.dll (Win32); `00xxxxxx` = Kingdom-Win32-Shipping.exe; `exe+0x...` / `0x14xxxxxxx` = Kingdom-Win64-Shipping.exe (image base 0x140000000).

## 1. Status
- **V37 = WORKING BASE** (verified in game): V30 + hero DataSet float slots [0x26],[0x27] = 1.0 (raw f32; same slots in the ReBorn DataSet). The hero walks.
- **Walking works for the whole battle with `走路輔助.bat`** (`tools\ue_inspect.py --walkhelper`, admin auto). Start it after the hero appears. It writes the hero Location into the sync object exe+0x195F340 at +0x14/+0x20.
- Works: lobby `gameStartup` launches Kingdom-Win64-Shipping.exe with `-bTCP` (client newudp=0); TCP connect; MsgConnect + ConnectAck; map loads; LoadingComplete; empty frames every 50 ms; ping 0x279c needs no reply; hero spawns.
- Best before V37: V18/19 (jump, attack, block OK; no ground walk).
- **Open issues:**
  - Sprint: double-W makes the client send 0x273e (uid) / 0x2778; no server reply yet.
  - NPC/object interactions react abnormally.
  - Pull-back: the native snap-back still teleports the hero ~10 m back to (0.5,-0.6). The walk helper masks it. **Permanent fix candidate:** call `KingdomPawn.ForceUpdatePlayerHumanLocation` through the .u patch pipeline (native exec thunk 0x140a51a50, vtable+0xaf8). Not built yet; no server-side entry.
  - V29 troops + AI + battle end: untested (walking now works, so test it next).
  - Results screen: unverified (section 5).
  - Duplicate hero (0x4e22 vs slave AddPlayer vs ReBorn, V11/V12): unresolved, low priority.
- **NEVER send CmdSync (0x4e20):** stuck loading.

## 2. Wire basics
- Stream cipher: ks[n] = A[n%256] ^ B[(n//256)%256]; n from 0 per connection/direction.
  - A: x=0x1f; for i: A[i]=x; x=((((x<<5)&0xff)+0xfd)*x+7)&0xff
  - B: c=0x3f; for i: B[i]=c; t=((c*0x7a)-0x31)*c&0xff; c=(t-0x1b)&0xff
- Frame: `u16 len` (counts itself), `u16 type`, body; little endian.
- Fields: uvar = LEB128; svar = zigzag LEB128; f16 = IEEE half; str = u16 len + bytes; vec = uvar count + items; bool = 1 byte.
- MsgFramework 0x2715 (S>C): varint f1 (unused), varint frameNo (from 1), u8 flag (2 = fragment), str payload = concatenated inner `u16 len|u16 type|body` slave messages. Flushed every 50 ms even when empty.

## 3. Message table
C = confirmed, H = layout from code, M = meaning inferred, G = guess. Full table: notes\battle\msg_dictionary.md.

| id | name | dir | body | status |
|---|---|---|---|---|
| 0x3e9 | MsgConnect | C>S | u32 1, u32 a (id), u32 1, u32 c (token) | C |
| 0x3ea | MsgConnectAck | S>C | varint code (0) | C |
| 0x3eb | MsgPing | S>C | varint a, varint b; client answers 0x3eb | H |
| 0x3ec | MsgMD5Check | ? | varint, str, str | CONFLICT: listed S>C; client sends one after spawn |
| 0x3f4 / 0x279c | ClientSystemInfo / ReqSelfPing | C>S | 0 + str " [Win64]" / 2 varints every 5 s | C |
| 0x2715 | MsgFramework | S>C | section 2 | C |
| 0x2721 | ReqMove (velocity-like) | C>S | uvar uid, f16 x,y,z (y always 0); sent while moving | H; do NOT echo as position |
| 0x2737 | ReqPosition | C>S | uvar uid, f32 x3 (position while moving) | H |
| 0x2738 | ReqMoveMode | C>S | uid, mode (1/2), f16 x3 velocity m/s (jump = (0,6,0)) | H |
| 0x2754 | ? | C>S | every ~100 ms after spawn | body unknown |
| 0x2770 | ReqTroopMove | C>S | | M (echo as Cmd 0x4ece) |
| 0x274d | ReqReBorn | C>S | | M (answer 0x4e80) |
| 0x2792 / 0x2796 | ReqSelectBornPos / Confirm | C>S | after CmdShowBornPos 0x4f03 | M (answer 0x4f04 / 0x4f06, untested) |
| 0x4e20 | CmdSync | S>C | varint, str | H. **X: stuck loading** |
| 0x4e22 | CmdAddPlayer | S>C | uvar uid, u8 isSelf, svar ptype (0 normal, 1 pending, 2 watcher), str name, uvar x2, str sname, uvar x4, vec<u8> face, uvar N + N*u32 DataSet, str | H; creates PlayerCtl; same uid twice = "Player Has Exist" |
| 0x4e23 | CmdAddCreature | S>C | uvar uid, uvar N, N*u32 DataSet | H; DataSet[1]: 1 soldier, 2 horse, 4 boss; owner DataSet[0x32] must be a live PlayerCtl |
| 0x4e4a | CmdControlAiPlayer | S>C | uvar uid | G/M: client runs AI for that PlayerCtl |
| 0x4e80 | CmdReBorn | S>C | uvar uid, uvar N, N*u32 DataSet, str name, vec<u8> | H; needs PlayerCtl; calls UE3 spawn (00e19260 remote / 00df26b0 local). **Pawn appears here** |
| 0x4e92 | CmdLoadingComplete | S>C | varint | C (leaves loading screen) |
| 0x4e96 | CmdCountDown | S>C | varint state, varint value | H; section 5 |

Slave msgs (Sync.dll 0x10034630):

| id | name | body | effect | status |
|---|---|---|---|---|
| 1 | AddPlayer | uid uvar, kind svar, f0c uvar, f10 uvar, pos f16 x3, dir f16 x3, f16, bool | player unit; needs top-level 0x4e22 first | H layout, M meaning |
| 2 | AddCreature (horse) | as 1 | | H |
| 3 | AddPerson (soldier) | uid, kind svar, f0c (0), f10 (camp), pos x3, dir x3, a uvar, b f16, c uvar | a = agentType key (agentparam.txt); missing key = NULL crash | H |
| 4 | AddBullet | uid, kind, 6 f16 | | H |
| 7 | Init | header only | callback +4 | H |
| 8 | BattleStart | header only | UE3 OnBattleStart: GameEngine flag 0x20000 + script events | H |
| 9 | BattleEnd | header only | SyncClient::OnBattleEnd (+0x228=1); UE3 reaction unknown | H |

## 4. DataSet (N x u32 LE)
- Use **N = 132** (UE3 reads index 0x7e; keep 4N + ~60 < 1024).

| idx | meaning | status |
|---|---|---|
| 0 | uid | H |
| 1 | creature type: 1 soldier, 2 horse, 4 boss | H |
| 2 | HEALTH (0 = remote dead). Hero 200, soldier 130 | M |
| 5,6,7 / 9,10 | dir x,y,z / pos x,y (raw f32; pos z = 0) | M |
| 0x10 | camp / team | H |
| 0x18..0x1b | helmet, shawl, armor, shoes ids (armor.txt) | M |
| 0x1e..0x21 | weapon 1..4 ids (meleeweapon / rangedweapon.txt) | M |
| 0x26, 0x27 | hero speed factors: must be 1.0f (V37 fix) | verified |
| 0x32 | owner uid (soldiers: hero uid) | H |
| 0x33 | SoldierKind: 1 foot, 2 archer, 3 cavalry, 4 horse archer; other = no pawn | H |
| 0x35 | commander uid (= hero uid) | M |
| 0x4c, 0x56, 0x57 | local player flagID, HairStyle | M |
| 0x4d | nonzero = mounted spawn | M |

- Current values: hero uid 10001, camp 1, hp 200, gear 17000011/17100001/17200001/17300001, weapons 18051001/18052001 (armytype 112011). Soldiers: hp 130, [0x33]=1.

## 5. Countdown, BattleStart, BattleEnd, results
- CmdCountDown(state, value) -> Kingdom 00ebfb00: 1 = prepare (freeze, timer UI); 2 = tick (value = seconds left; 0 = unfreeze); 3 = running. Used: (1,3)(2,3)(2,2)(2,1)(2,0)(3,0), 1 s apart. Ignored without hero, GameEngine and local controller.
- BattleStart = slave msg 8. BattleEnd = slave msg 9 in a frame, optionally with top-level 0x4e73.
- bMatchHasBegun (GRI+0x1cc bit 2) is set only by native 0x753e10 when bStopCountDown is set; no Sync Cmd sets it.
- Results: the UE3 exe never reports to the lobby. The frontend reads lobby pushes `gameResultGlance` / `gameResult` (omit nested objects). Process exit returns to lobby. Not verified in game yet.

## 6. Configs, maps, key functions
- Configs: notes/decrypted/cfg/ (tools/cfgdec.py; row 1 names, row 2 types, data from row 4). Map ids: notes/map_ids.md (17 = training ground).
- Key functions: SyncClient 0x100afab0 / 0x100b00b0 AddPlayer/ReBorn, 0x100afdc0 AddCreature, 0x100af840 Framework; Sync.dll 0x10034630 slave dispatcher; Kingdom 0x00e19260 / 0x00df26b0 pawn spawn, 0x00ebfb00 countdown.

## 7. Walking, speed and snap-back
- Walking gate solved by V37. The client's speed comes from controller fPersonToSelf/HorseMaxSpeedFactor = max(slot,1e-4) (Win64 0x140aee73f / 0x140aee765), read from DataSet 0x26/0x27. Dead ends (script gates, challenge flags, root motion, collision, memory-written speed factors, server Cmd echoes): see the archive report and notes\battle\walk_gate_*.md.
- Snap-back (hypothesis ~60%, Win64 Ghidra + CE trace): sync object DAT_14195f340 (+0x14 base pos, +0x20 working), pawn DAT_14195f338. Callback FUN_140ae0370 (MultiPointCheck x5 + FarMoveActor pawn -> obj+0x20) is the teleport. Setter FUN_140aaf020 (vtable-only) writes obj+0x14; nothing calls it, so +0x14 stays at spawn. The leash check and the setter caller are not traced.
- FUN_140aaf020 = native UScript `KingdomPawn.ForceUpdatePlayerHumanLocation(Vector)` (exec thunk 0x140a51a50, vtable+0xaf8). No server-side entry.
- Failed (client did not react): echoing each 0x2737 position as Cmd 0x4eca (V38/V39), and in-frame slave 401/402/403 (V41/V42).
- Key J of `英雄速度檢查.bat` reads the sync object.
- Reports: 20261107_2200_pullback_echo, 20261108_0000_sync_position_feed, 20261108_0100_v41_log_check, 20261108_0200_snapback_writers, 20261108_0300_walk_helper.
