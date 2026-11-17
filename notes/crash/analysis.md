# Crash analysis: frontend.exe dies right after our getSelfInfo reply (2026-11-04)

## Root cause [C]
`getSelfInfo` sent `"forbidmatch": 0` (a scalar). The DLL parser for that route (response case 19, `PoClientDLL.dll` 0x10037f97)
reads `info["forbidmatch"]["forbid"]` and `info["forbidmatch"]["outTime"]`, i.e. it **indexes into** `forbidmatch`.
jsoncpp's `Value::operator[](const char*)` (0x1008fa00 -> 0x1008fa20) assumes the Value holds a map pointer once its type flag is set,
so for an int Value it treats the integer 0 as a `std::map*` and the map lookup (0x10090740) dereferences NULL.
Missing keys are fine (a missing key yields a null Value that is converted to an empty object); only a wrongly typed scalar crashes.
This is why the other routes answered with a bare `{"code":0}` never crashed.

## Evidence
Both dumps (211616, 211640) and the game's own `ERRORLOG 20261104 2116xx.log` are identical:
- Exception 0xC0000005 ACCESS_VIOLATION, "Read from location 00000000", EIP 0x622c0745 = **PoClientDLL.dll + 0x90745** (VA 0x10090745, image base 0x10000000).
- Instruction: `mov edi, [ecx]` at the top of the `std::map` lookup 0x10090740 (`push ebp; mov ebp,esp; push esi; push edi; mov edi,[ecx]`), ECX = 0, EDI = 0.
- Call chain (ebp walk): 0x10090740 <- 0x1008fa20 (`Value::operator[]`, ret 0x1008fadf) <- 0x1008fa00 wrapper (ret 0x1008fa0d) <-
  **0x10038dc8** (ret 0x10038dcd, inside the getSelfInfo case) <- big parse function (0x1008ab53) <- frontend.exe 0x465fba (network worker thread).
- At 0x10038db1..0x10038dc8 the code pushes the strings `"forbidmatch"` (0x1019f580) and `"forbid"` (0x1019f578) and calls operator[] twice.
  Both string addresses are on the crashed stack (0x623cf580 / 0x623cf578 = base 0x62230000 + 0x19f580 / 0x19f578).
- The log has no `OnGetSelfInfo` line because the crash is inside the parse, before the frontend callback (vtable +0x344) runs.
  Crash ~0.6 s after our reply = the next network-thread read.

## Real getSelfInfo `info` layout (corrected) [C from disassembly 0x10037f97..0x100393e0]
Flat scalars/uints as listed in `lobby/login_flow.md`, plus:
- `pveinfo`: object `{degree1Win, degree2Win, degree3Win}`
- `forbidmatch`: **object** `{forbid: bool, outTime: uint}`. There is no top-level `forbid` key read (the earlier "forbid" in the schema output was the inner key).
- `tutorialAward`: array of **bool**, only the first 5 are read.
- `soldierexp`: array of objects `{country, stage, exp}` (uint each), at most 0x14 = 20 are read, stored as 12-byte `{stage,country,exp}` rows.
  Top-level `country`/`stage`/`exp` arrays do not exist (they were a misreading of schema.py output). The frontend lookup
  (`GetPlayerSoldierexpInfo(country, level)`, frontend 0x8b0d80) is a linear search over 20 rows and returns 0 when absent, so empty is safe;
  we send 3 rows (country 1..3, stage 1, exp 0) as a realistic default [country meaning G].
- `faces`: uint array, `hungup`, `maliciouslogout`, `jade`, `forbidtalktime`, `ceVal`, `preCeVal`: uint.

## Other routes decoded (all in `handlers.py`)
| route (case) | response | notes |
|---|---|---|
| getSignInInfo (69) | `{code, signinMonth, signinData, resigninNum, singninCount, signinreward:[uint], treegiftdate}` | key really is spelled `singninCount` |
| getOnlineInfo (74) | `{code, onlinedate, onlinetime, onlinehadreward}` | |
| queryVipBuySort (201) | `{vipBuySorts:[{days, gold, rebate}]}` | rows from `lua_config/VIP.lua` (7/30/180/360 days) |
| chargeHandler.getList (206) | `{code, data:[{id, num, steps:[uint]}]}` | |
| getBattleProfitMultiInfo (208) | `{code, data:[{id, des, deadline:[{type,date1,date2,week:[]}], armytype:[], gamemode:[{main,sub}], winjudge:bool, isArmyFirstWin:bool, times, moneymulti, expmulti, armyexpmulti, heroexpmulti, generalexpmulti, exploitmulti}]}` | empty = no bonus events; Lua `SodierCard_ManyExp` returns early |
| loadStoreBuyLimit (23) | `{code, limitinfo:[{itemtypeid, num}], fleebox:{buycnt, buytime}}` | `fleebox` is indexed into: must be an object (or absent) |
| loadRoleItem (47) | `{code, isfinal, capacity, serieNum, items}` | |
| reqStoreInfo (77) | `{version, isfinal, serieNum, items}` | |
| loadRoleEmail (102) | `{code, curDaySend, isfinal, serieNum, items}` | |
| loadRoleTask (192) | `{code, dailyTasks:[], dailyRefreshCount, limittimeTasks:[], commonTasks:[]}` | task row `{taskid, complete, sche1-3, notaward:bool}` |
| joinChatChannel (221) | `channel,port,degree,token` are uint, `host` string | we used strings for channel/token; harmless but fixed |

## General rule for the fake server
For any key the DLL indexes into, the value must be an object/array (or absent), never a scalar and never a string.
Scalars read as "if present and convertible else 0" are safe with any type. Arrays are indexed with `size()` bounds, and the
only fixed caps found are 5 (tutorialAward) and 20 (soldierexp).

## Still guessed / could crash next
- Exact `items` row layouts of the paged routes (loadRoleItem, reqStoreInfo, loadRoleEmail, loadTechInfo) are not decoded; we send empty arrays.
- getSelfInfo was only checked from `forbidmatch` onwards for scalar-vs-object; everything before is flat scalars/`pveinfo`/`faces` which we send correctly.
- Later routes in the loading sequence (frontend-side handlers after OnGetSelfInfo) have not been run yet; the frontend's own handler for
  `info` (vtable +0x344) was not disassembled, so a crash there is possible.
- Chat: `joinChatChannel` points at 127.0.0.1:3015 (the lobby itself); a failed chat connect might misbehave.
