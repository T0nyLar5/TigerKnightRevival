# Lobby login flow: data loading after entry (section 3)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [login_flow.md](login_flow.md) (table of contents). Response shapes read from the PoClientDLL parser.

## 3. Data loading after entry
Order and request bodies: [G] (bodies not decoded; probably `{}` or simple keys). Response schemas below are [C] from the DLL parser. Every response carries `code` (0 ok).
Lua `GetAllDataSucess` fires once the frontend has all required data (completion condition not traced).
Likely sequence [G]: getRoleState (108), getSelfInfo (19), loadRoleItem, loadPropBar (85), loadRoleSuit (44), getSoldier, loadTechInfo, getRankOpenInfo,
queryScienceTypeOpenInfo, reqStoreInfo (77), loadRoleEmail (102), loadRoleTask (192), getSignInInfo (69), getOnlineInfo (74), queryServerTime (128),
queryAllAssets (218), getChatConnectorsInfo (222) / joinChatChannel (221), matchHandler.restore (only if restore==true).

- getRoleState (108): `{code, uid:str, tutorialStep:uint, vipvalidtimesec:int, forbidtalktime:int}`. Frontend: code 0 or 2 accepted; tutorialStep > 4 goes straight on, Lua keeps TUTORIAL=tutorialStep (<4 forces tutorial screens, 0 starts role creation). Use 4+.
- getSelfInfo (19) [C, decoded from disassembly, see `notes/crash/analysis.md`]: `{code, info:{identity, uid, name, level, experience, sex, gold, barracksnum, score, copper, fleecoin, generalexp, vipvalidtimesec, noviciatestage, helpPanel, liveShow:bool, signinMonth, signinData, resigninNum, onlinedate, onlinetime, onlinehadreward, faces:[uint x14], faceicon, faceframe, autosupplyflag:bool, autorecruitflag:bool, voice, exploit, pveinfo:{degree1Win,degree2Win,degree3Win}, native, cheatnum, cheatnumtotal, forbidmatch:{forbid:bool, outTime:uint}, hungup, maliciouslogout, jade, tutorialAward:[bool x<=5], soldierexp:[{country,stage,exp} x<=20], forbidtalktime, ceVal, preCeVal}}`.
  **`forbidmatch` MUST be an object**: sending a scalar crashed frontend.exe (access violation, PoClientDLL+0x90745, jsoncpp operator[] on an int). There are no top-level `forbid`/`country`/`stage`/`exp` keys. noviciatestage < MAX_NOVICIATESTAGE triggers the newbie guide.
- GENERAL RULE [C]: for any key the DLL indexes into (object or array), send an object/array or omit it; never a scalar. Plain scalar keys tolerate any JSON type (read as "if present and convertible else 0").
- getSignInInfo (69): `{code, signinMonth, signinData, resigninNum, singninCount, signinreward:[uint], treegiftdate}` (sic `singninCount`). getOnlineInfo (74): `{code, onlinedate, onlinetime, onlinehadreward}`.
- queryVipBuySort (201): `{vipBuySorts:[{days,gold,rebate}]}`. chargeHandler.getList (206): `{code, data:[{id,num,steps:[uint]}]}`. getBattleProfitMultiInfo (208): `{code, data:[{id,des,deadline:[{type,date1,date2,week:[]}],armytype:[],gamemode:[{main,sub}],winjudge:bool,isArmyFirstWin:bool,times,moneymulti,expmulti,armyexpmulti,heroexpmulti,generalexpmulti,exploitmulti}]}`. loadStoreBuyLimit (23): `{code, limitinfo:[{itemtypeid,num}], fleebox:{buycnt,buytime}}`.
- Real "paged" shapes differ per route [C keys, G row layouts]: loadRoleItem `{code,isfinal,capacity,serieNum,items}`, reqStoreInfo `{version,isfinal,serieNum}`, loadRoleEmail `{code,curDaySend,isfinal,serieNum}`, loadRoleTask `{code,dailyTasks[],dailyRefreshCount,limittimeTasks[],commonTasks[]}` (task `{taskid,complete,sche1,sche2,sche3,notaward:bool}`), loadTechInfo `{code,...}`.
- queryServerTime (128): `{ServerTime:uint (unix secs), DeltaUTC:int}`.
- loadPropBar (85): `{code, propbar:[{itemtypeid,num,pos}]}`.
- loadRoleSuit (44): `{code, suits:[{shoes,helmet,armor,shawl,horse,saddle,hoof,strike,horseadd,weapon1-4,fashion,fashion1-7,banner,markflag,flee_helmet,flee_shawl,flee_armor,flee_shoes}]}` (string values).
- queryAllAssets (218): `{code, start, assets:[{asset_id,container_id,product_class_id,asset_quantity}]}`.
- joinChatChannel (221): `{code, channel, port, degree, token, host}`; getChatConnectorsInfo (222): `{code, chatDegree:[int]}`. Chat is a second Pomelo server (`chatconnector.chatHandler.entry`) at host/port from these; whether failure is tolerated is [G].
- matchHandler.restore (109): `{code, addr:[{ip,port}], subGameMode, gameMode, token, playerId, camp, mapId, gameType}`; only when restore==true.
- Paged lists (loadRoleItem, reqStoreInfo, loadRoleEmail, loadTechInfo ...) use `isfinal, serialNum, pageindex, totalpage, totalsize, pagesize, items[]`; send a single page with isfinal true [G].
- Any other route: `python -I tools/schema.py <PoClientDLL.dll> 10033f70 1005dbcc 244 <route index...>` (indices in `notes/route_table.txt`).
