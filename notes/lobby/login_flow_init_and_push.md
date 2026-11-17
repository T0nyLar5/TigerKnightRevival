# Lobby login flow: init chain 3b and push routes (section 4)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [login_flow.md](login_flow.md) (table of contents).

## 3b. Loading-screen completion (LoadLoginMsg / SetInitInfoFlag) [C from frontend.exe disassembly]
The init is a **serial chain**, not a parallel load. `SetInitInfoFlag(N)` (frontend 0x877470) sets bit N in a mask (this+0x5c), fires Lua `NormalWaiting_Loading(tip=N)`, then calls
`LoadLoginMsg(N)` (0x866770) which runs step N+1 from a map built at 0x866270 (key -> member fn; the log prints N+1). `GetAllDataSucess` fires once the mask == 0xFFFFFE (flags 1..23 ALL set, 0x877670).
Flag N is set by the response handler of step N, and only when `code==0` and `isfinal==1` for paged ones (absent keys default code=1/isfinal=1 as seen in the log).
Steps/flags: 1 login, 2 getRoleState, 3 queryServerTime, 4 getSelfInfo, 5 getRoleEquipment, 6 getSoldier{serieNum:1}, 7 loadRoleAssistant, 8 enumerateFriends,
9/10/11 getRankOpenInfo nation 1/2/3, 12 loadRoleSuit, 13 loadRoleItem, 14 loadRoleEmail, 15 reqChallengeBaseInfo, 16 syndicateHandler.getSynInfo, 17 getRankOpenInfo nation 8,
18 matchHandler.queryMatchModeTime, 19 friendHandler.getBlackList, 20 / 21 getRankOpenInfo nation 5 / 999, 22 queryScienceTypeOpenInfo, 23 joinChatChannel [G for 23, 12-14 by callback slot].
**Why it stuck at "載入好友列表"**: flag 9 is chosen by switching on the response's `nation` (1->9, 2->10, 3->11, 5->0x14, 8->0x11, 999->0x15). Our `{"code":0}` had no `nation` -> eNation 0 -> no flag, chain dead.
getRankOpenInfo reply = `{code, nation (echo request!), serieNum, isfinal:1}`. No server push is needed for the chain.
New schemas [C]: getRoleEquipment `{equiplst:[uint]}`; getSoldier / queryScienceTypeOpenInfo `{isfinal, serieNum}`; loadRoleAssistant `{heros:[{id,exp,coatmask,haveflag[],idcoat,timevalid,loyalty,forwardhero}]}`;
enumerateFriends `{friendsInfo:[..], freqs:[..]}` rows `{uid,name,sex,level,vip,state,syndName}`; getBlackList `{list:[..]}`; queryMatchModeTime `{modes:[{mode,subMode,startHour,endHour,startDay,endDay}]}`;
reqChallengeBaseInfo `{challengephase, proficiency[], firstcomplete[], topscore[]}`; getSynInfo `{code, data:{id,name,...,flag:{id,color,icon,iconPos}}}` (data and flag are indexed -> objects).

## 4. Push routes
Names of the 163 push events (friendTalk ... livenessUpdate) are in the DLL .rdata right after the route table; dispatcher is DLL 0x10002500. Possibly early: `loginWait`, `healthStatus`,
`updateGold/updateMoney/updateGeneralExp/updateExploit/updateExpAndLev`, `cheatInfo`, `turorialInfo`, `sysMsg`, `refreshEmail`. None is known to be required to reach the lobby [G].
