# Lobby protocol: unlock state, tech actions and known gaps
> rev 2 | 2026-11-08 02:22 | prepareMatchRoom / chgMatchRoomBattleInfo handlers + mode-2 joinMatch opens the troop window
Summary: unlock-all state and push-delivered rows (tools/unlock_all.py), help panels and max level, the soldier-tree freeze fix, and the known route gaps.
Source: notes/lobby_protocol.md sections 'Gaps' to 7 (text moved unchanged, split 2026-11-06).

## Gaps
- Request bodies of the load requests and the frontend's exact completion condition for GetAllDataSucess (trace OnLogin's call through the second interface vtable slot 0x1ec, then the frontend per-response handlers, vtable at frontend 0xd199bc).
- Row layouts of paged `items` arrays (loadRoleItem, reqStoreInfo, loadRoleEmail, loadTechInfo); frontend-side handling of getSelfInfo `info` (vtable +0x344).
- Whether chat connector failure blocks the lobby.

## 5. Unlock-all state, push-delivered rows, tech actions (tools/unlock_all.py)
- **Row data arrives as server PUSHES, not in the response** [C layouts from DLL dispatcher 0x10002500, G delivery]. Push names = `loadRoleItem, getSoldier, reqStoreInfo, getRankOpenInfo, queryScienceTypeOpenInfo, loadRoleEmail`; body is one page
  `{totalsize,pagesize,totalpage,pageindex,isfinal,serieNum,items[],(nation)}` (a `msgs:[page,..]` wrapper is also accepted). handlers return `_push:[(route,body)]`, lobby.py sends those before the response.
  Rows: getSoldier/establishArmy `{id,amount,sequence,exp,helmet,shoes,armor,shawl,horse,saddle,hoof,strike,horseadd,weapon1-4,fashion,skill1-8,lastwinTime}`; getRankOpenInfo `{rank,nation}`; queryScienceTypeOpenInfo plain uints;
  loadRoleItem `{id(str),type,uid(str),endurance,num,timeout,commonused}` (not filled: item ids unknown); openTechType push `{techlist:[{techid,techtype}]}`.
- **The game's data tables (rank_tree, armytype, fujiang, itemtype ...) are inside encrypted `frontend/bin/config.cfg` (not cracked; the client logs `Config Err: File armytype Index:213029`).** There is no lua_config table for them.
  Known IDs come from `frontend/bin/data/TechTreeData/*.zqk`: rank ids (101-123 Wei, 201-224 Shu, 301-326 Wu, 501-510 Roman, 802-848 Special, 999 exploit) and 1097 tech ids (>=1000, 3rd column = type). Nations: 1 Wei 2 Shu 3 Wu 4 Xiliang 5 Roman 8 Special; stages 1-3.
  Army ids look like `<rank><3 digits>` (101006, 112018, 213028 ...), suffixes unknown, so soldiers/heroes/items are NOT pre-filled.
- Actions [C keys]: openRank `{rankid,prerank}`->`{rank}`; openScience `{scitechid,scitechtype}`->same; buySoldier/sellSoldier `{armyid}`->`{armyid}` (buy also pushes establishArmy and is stored in player.json `soldiers`);
  operArmyAttr `{armyid,opertype,data}`; buyRoleEquipment `{scitechtype,equiptype}`; buySoldierEquipment `{scitechid,equiptype}`; getSoldierEquipment `{rank}`->`{rank,equiplst}`. Equipment/attr changes are echoed, not stored.
- Currencies are uint32 (asUInt); unlock_all sets gold/copper/generalexp/exploit/jade/fleecoin to 99,999,999. soldierexp: 6 nations x 3 stages = 18 rows (cap 20).

## 6. Help panels, max level (2026-11-04)
- `userHandler.setHelpPanel` request `{val:uint}`, response only `{code}` [C, DLL case 242]. Lua `GetHelpPane_lua(stage)` / `SetHelpPane_lua(stage)` (PlayerData) are used for stages 1 Store, 2 TechTree_Sodier (the 升級 page), 3 LieutenantInfo, 4 MainMode / NewbieGuide_MainMenu; the client sends `val` = 1,2,4,8 (one bit per stage) [bitmask: C from the log values, G for exact bit math].
  getSelfInfo `helpPanel` is the saved mask. Server now sends 0xFFFF (all seen), stores/ORs `setHelpPanel` into player.json, and always forces 0xFFFF. noviciatestage=99, tutorialStep=5, tutorialAward all true were already set.
- Max player level = 60 (BattleSettlement.lua clamps `Lv60` for level >= 61). Server sends level 60 / experience 999999999 in auth accounts[], getSelfInfo and player.json (`State` forces it on load; `tools/unlock_all.py` writes MAX_LEVEL/MAX_EXP). The `role_levexp` exp table is in encrypted config.cfg (not available), so experience is just a big value; mode-unlock checks are `GetPlayerLevel_lua() >= OpenLev` in Lua.
- Battle routes now answered: `matchHandler.joinMatch` (tutorial and single modes), `createPveBattle` (`{mapid,degree,roomId}`), `startPveBattle`, `customRoomHandler.startGame`, `clientStartGameFail`, `leaveMatch`, `queryCrusadeMatchPunish`, `setTutorial` (see battle_launch.md section 9).

## 7. Freeze when unlocking soldier-tree equipment (fixed 2026-11-05)
- Ack of `openScience` does nothing on success (frontend FUN_00878bf0 only posts `on_ScienceTypeOpenFail` for code!=0). Success is driven by the PUSH `openTechType {techlist:[{techid,techtype}]}` (DLL push case 23) -> Lua `TechTree_UpdateOpenTech` hides the `NormalWaiting` overlay. Without it the UI looks frozen. handlers.open_science now pushes it.
- `unlock_all.py` now also fills soldiers (armytype, 94), heroes (hero_type, 27), bag items (itemtype type 0, 1283), science nodes (science_tree) and role equipment (science_type sci_type 1, 719). Hero row semantics (coatmask/haveflag) and item row semantics are guesses.



## Pre-battle troop window (2026-11-08)
`joinMatch` mode 2 now pushes `matchRoomPrepareInfo` (opens Combat_Readiness); `prepareMatchRoom` replies `{code,suit,armyid}` then pushes `matchRoomPrepare` + `gameStartup` (armyType = chosen). `chgMatchRoomBattleInfo` replies the same shape. Env `TK_PREBATTLE` (unset = mode 2, `0` off, `all`). reqRolePreBattleInfo is unused by the client. Details: reports\20261108_0222_prebattle_troop_select.md. Untested in the real client.