# Pre-battle troop selection (lobby) and spawn-point selection (battle): static research
> rev 5 | 2026-11-08 03:06 | default battle troop clamped to an owned troop in the listed stage (M+1 hypothesis)

Trigger: owner watched old videos: (1) lobby window to pick a troop type, (2) in-battle countdown to pick a spawn point, (3) battle starts. Our flow skips both.

## A. Lobby side (verified static unless marked H)
- The window is the Lua frame `Combat_Readiness` (notes\scripts\ui\Addons\Combat_Readiness\Combat_Readiness.lua) plus the SodierCard panel. Flow in the real game (modes with a match room, e.g. crusade mode 2):
  `matchHandler.joinMatch` -> push `matchSuccess` (accept window, mode 2) -> `acceptEnterMatch` -> push `matchRoomPrepareInfo` (Lua cb 108 `On_NotifyMatchRoomPrepareInfo`: shows Combat_Readiness, 50 s timer) -> player picks troop/suit/hero -> Ready click or timeout calls `Command_PrepareMatchRoom` -> request `matchHandler.prepareMatchRoom` -> response (cb 109) -> push `matchRoomPrepare` (cb 110) -> `gameStartup`.
  Changing troop inside the window: request `matchHandler.chgMatchRoomBattleInfo`. Tutorial/challenge modes (1,4,5) never open it (tutorial goes joinMatch -> gameStartup).
- Pre-selection happens in the main menu BEFORE pressing 出戰: MainMenu_BtnFighting.lua calls `SetUsedSodier_lua(SodierCard_GetSelectedId())`.
- Field layouts (PoClientDLL builders/parsers, keys from tools\fnkeys.py):
  - req prepareMatchRoom `{suit, armyid, roomId, usepvetoken}`; req chgMatchRoomBattleInfo `{suit, armyid, roomId}`; both reply `{code, suit, armyid}`.
  - push matchRoomPrepareInfo `msgs[{mode, subMode, mapId, maxArmyClass, roomId, roleInfos[{uid, level, camp, armyType, vip, bAi, faceicon, faceframe, name}]}]`; push matchRoomPrepare and matchRoomChgBattleInfo `msgs[{armyid, roomId, uid}]`. (Key-to-push assignment by order in the parser = hypothesis M; the key sets themselves are verified.)
  - reqRolePreBattleInfo (route 76, `{suit, armyid, hero1, hero2}`): builder exists in the DLL, but no Lua and no frontend string references it; it is NOT part of this flow (likely unused). Unhandled is harmless.
- `soldier:` in the frontend log (OnNotifyGameStartup 0x86e1a0, disasm 0x86e75f-0x86e8cc): it is a LOG ONLY. Per player it takes `playerInfos[i].armyType` (struct +0x10), looks it up through a singleton config table (0x69a070 / 0x6dc900) and prints the soldier name. Empty because our armyType was 0. It is not an input to the battle.
- The UE3 command line carries no army/soldier parameter (launch_flow_cmdline.md section 2). So the battle exe learns the chosen army only from the battle server (AddPlayer DataSet / 0x4e23).

## B. Battle side (hypothesis, nothing sent yet)
- Messages: S>C `CmdShowBornPos` 0x4f03 (open spawn-point picker), C>S `ReqSelectBornPos` 0x2792, C>S `ReqSelectBornPosConfirm` 0x2796, S>C `CmdSelectBornPos` 0x4f04 / `CmdSelectBornPosConfirm` 0x4f08 (catalog) or 0x4f06 (older note; the catalog lists 0x4f08, so verify), `CmdShowBornPosSpecialPoint` 0x4f0f, `CmdRebornWaitTime` 0x4e8c, `CmdCountDownUpdate` 0x4e96 (we already use it), `ReqReBorn` 0x274d -> `CmdReBorn` 0x4e80 (hero pawn spawn).
- Our flow sends 0x4e80 ReBorn immediately with a fixed position, so the picker never opens. A faithful flow would be: countdown prepare (0x4e96 state 1) -> 0x4f03 with the camp's spawn points -> wait for 0x2792/0x2796 -> answer 0x4f04/0x4f08 -> then 0x4e80 at the chosen point. Bodies of 0x4f03/0x4f04/0x4f08 are undecoded, so no V47 (not grounded).

## C. Do troops spawn client-side from `soldier:`? (verified static: no)
- `soldier:` is a log of armyType, the command line has no army data, so the UE3 client cannot derive troops from lobby data by itself. The server still has to send 0x4e23 + AddPerson (research_troops_creation.md). Lobby-side `armyType` may still matter indirectly if the real battle server forwards it; the client-side pawn lookup (GetSoldierInfoBySoldierID) uses ids from the 0x4e23 DataSet (V44 already sent 112011).
- Caveat: V44 got no reaction in mode 5; the mode-2 class (vs computer) is still untested with a running battle server.

## Implemented (server\handlers.py, tools\selftest_lobby.py; offline selftest ALL PASSED)
- `joinMatch` for gameMode 2 now pushes `matchRoomPrepareInfo` instead of `gameStartup` (env TK_PREBATTLE: unset = mode 2 only, `0` = old behaviour, `all` or `2,3` lists).
- New handlers `prepareMatchRoom` (reply, then push matchRoomPrepare + gameStartup with `playerInfos[0].armyType` = chosen armyid) and `chgMatchRoomBattleInfo`.
- Not run against the real client. Risks (H): the window may need extra state (GetEnterMatchType); the window opens with an empty 5-6 slot roster; if Ready does nothing, the 50 s timer auto-sends prepareMatchRoom. player.json backed up (backup\player_before_prebattle_20261108.json) and restored after the selftest.

## Owner test
Start via 一鍵測試_選版本.bat, variant 44, map 3 (or any), battle server running. In the lobby pick the vs-computer mode, press 出戰. Expected: the 戰備 window (Combat_Readiness) opens with a countdown; pick a troop, press Ready (or wait 50 s). Then the battle starts. Send the lobby log (look for `prepareMatchRoom`). To get the old behaviour set TK_PREBATTLE=0.

## Crash follow-up (owner test 02:24: frontend.exe "Runtime Error / terminate in an unusual way")
- Evidence (verified): lobby log shows joinMatch reply {code:0} then push matchRoomPrepareInfo; the client log ends at "Begin Match ... idArmyType:812024"/JoinMatch_lua with NO "OnNotifyMatchRoomPrepareInfo" line, so it died inside the DLL parser, before the frontend handler.
- Cause (high confidence, static): the DLL parser reads `roleInfos[].uid`, `roomId` (and uid/roomId in matchRoomPrepare / matchRoomChgBattleInfo) with type tag 4 = string (isConvertibleTo then asString). We sent `uid` as a JSON number. The bundled jsoncpp asString on a numeric value throws, nothing catches it, abort() -> that dialog. Same rule as gameStartup (roleId string). Hypothesis only for the exact jsoncpp version; the string typing itself is verified from the disassembly.
- Other fields checked against the parser: mode/subMode/mapId/maxArmyClass/level/camp/armyType/vip/faceicon/faceframe uint (ok), bAi bool (int 0 convertible, ok), name string, roleInfos array of objects, msgs array. armyid is uint.
- Fix: uid sent as string in roleInfos and in matchRoomPrepare. Selftest now asserts string uid/roomId; ALL PASSED. TK_PREBATTLE=0 fallback unchanged.

## Hang follow-up (owner test after f2b8400: "匹配中" forever)
- Verified (client log 02:32:23): matchRoomPrepareInfo WAS parsed and Lua `On_NotifyMatchRoomPrepareInfo` (cb 108) ran, but the joinMatch response callback (cb 100, `MainMenu_Fighting_On_JoinMatch`) ran AFTER it in the same moment and drew the matching overlay (TK_RecoverToInitLayout / ShowMatching) over/instead of the 戰備 window. Both packets arrived together (push sent right after the response). The client sent nothing more except an UNHANDLED `reqRolePreBattleInfo {armyid:812024,hero1:0,hero2:0,suit:0}` (so it IS used, on troop select).
- Fix (hypothesis that the order is the cause, ~65%): push delayed 2.5 s after the response (`_push_after` items may now be `(route, body, delay_s)`; lobby.py uses call_later; env TK_PREBATTLE_DELAY). reqRolePreBattleInfo answered `{code:0}`. TK_PREBATTLE=0 fallback kept. Selftest ALL PASSED.

## Troop list / suit / voice follow-up (owner test of 730ef46 + 21ff928)
- Client log (verified): client selected idArmyType 812024 itself (BarrackData current soldier), sent PrepareMatchRoom suit:0 armyType:812024; our reply echoed it and gameStartup followed. Our roleInfos armyType was 0 ("SetMatchRoomPrepareInfo armyType = 0") -> broken icon.
- Cause of empty list (verified Lua, value guess = hypothesis): Combat_Readiness_ModeRest (non-PVE branch) calls SodierCard_Box_SetStage(armyclass, armyclass) with armyclass = our `maxArmyClass`; Lua only knows stages 1-3 and we sent 4, so the troop box was filtered to a stage nobody has. Now `maxArmyClass` = 3 (env TK_ARMYCLASS to change; try 1 or 2 if the list is still empty/odd).
- Cause of broken default icon (verified data): owner's soldier list contained 10 special NPC troops (soldiers.txt SoldierSubKind 8xxx, e.g. 812024 氐人游骑, 812001) and the client defaulted to 812024. The getSoldier push now hides SubKind 8xxx rows (player.json untouched). Playable ones remain (82 rows).
- roleInfos[].armyType now = last army reported by the client's reqRolePreBattleInfo (only if owned+playable), else 0.
- What the lobby carries now: gameStartup.playerInfos[0].armyType = armyid from prepareMatchRoom (client-chosen, was 812024 NPC, now a playable id); heroType 0; NO suit and NO equipment ids in gameStartup (the DLL parser has no such keys). The chosen suit index is only in prepareMatchRoom {suit}. For the battle-server agent: lobby now writes server\data\last_prebattle.json = {armyid, suit, suit_row} (suit_row = equipment-id map of player.json suits[suit], keys are slot numbers) on every prepareMatchRoom, so battle_server.py can use the owner's worn gear instead of the tutorial set.
- Voice (documentation only): newUser saved voice (player.json voice=101) and getSelfInfo/role info send `voice` from it, so the lobby part is present; in-battle voice would need the battle server/DataSet, not investigated.
- Note: my stop_servers.ps1 call during the selftest also stopped a python process on port 7777 (another agent's battle server); restart it if needed.

## Stage filter vs default troop (owner test with maxArmyClass 2, 2026-11-08 ~02:58 log)
- Verified (client log 02:58:02/07): client picked 112014 (中原重矛手, soldiers.txt Level 5 = stage 2) and sent it in reqRolePreBattleInfo and prepareMatchRoom. The owner saw only 3-star troops selectable, so 112014 was not in the list.
- Stage rule (verified Lua): ServerEnum.lua EArmyStagLev 1=Lv1-4, 2=Lv5-7, 3=Lv8-10. Combat_Readiness non-PVE branch calls SodierCard_Box_SetStage(armyclass, armyclass), and SodierModel:getSodierInfo filters `min <= stage <= max`.
- Conflict (hypothesis): by the Lua alone maxArmyClass 2 should list stage 2 (Lv5-7), which includes 112014. The owner saw stage 3. The fit that explains all observations (M=2 lists 3-star; M=4 empty; M=3 blocked) is that the C++ side maps maxArmyClass to the list stage as M+1 (same +1 offset as GetPveTokenRoomInfo `armyclass = degree + 1`). Not verified in C++.
- Fix (server\handlers.py only): `_effective_army` picks the battle troop. An owned playable troop outside the listed levels (`_STAGE_LEVELS[maxArmyClass+1]`, with M=2 -> Lv8-10) is replaced by the first owned listed troop in getSoldier order (510009 精銳禁衛軍, Lv10, sequence 1). Ids the owner does not own (e.g. test id 812001) are kept as sent, so the selftest still passes. Used in roleInfos armyType, prepareMatchRoom reply + gameStartup + last_prebattle.json, and chgMatchRoomBattleInfo. maxArmyClass stays 2 (env TK_ARMYCLASS).
- Caveat (hypothesis): the client window still pre-selects its own troop (112014) and shows it in the roster until the server answers. The battle uses 510009. player.json not changed. Offline selftest ALL PASSED. Not run in the game.
- Owner check next: expect the battle troop to be 510009 (lobby log `prepareMatchRoom` reply armyid 510009). If the list is still wrong, try TK_ARMYCLASS=1 (list would be stage 2, Lv5-7) and adjust `_effective_army`.
