# Battle results and open questions (2026-11-05)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary: lobby battle result pushes (gameResultGlance, gameResult), other findings, and the ranked open questions from the 2026-11-05 free exploration.
Conf: see the H/M/L legend in [README.md](README.md).
Source: notes/research_free_1105.md sections 4-6 (text moved unchanged, split 2026-11-06).

## 4. Battle results (lobby pushes `gameResultGlance`, `gameResult`) [keys H from PoClientDLL key strings; nesting M]
Extractor: `tools/pushkeys.py` (ordered json keys + accessor type from a PoClientDLL parse function; range 0x10013400-0x10018000). Both pushes wrap their payload in `msgs:[ {...} ]` like gameStartup.
- `gameResultGlance` (summary shown to everybody): `gameMode, subGameMode, mapId(uint), battleId(str), victoryCamp, roomId, ..., mtype, appraiseAdvise[], players[{uid(str), name, level, TeamIndex, unScore, bDead, bMvp, sname, vip, armyType, heroType, bAi, bNegativeGame, bAbnormalState, bCheat, bHungUp, bMaliciousLogOut, faceicon, faceframe, oldscore, newscore, pveEpicsData{unKillEnemy,unKillBossNum,unRebornNum,unRebornAllNum}, pvpCrusadeData{unKillPlayerNum,unKillFujiangNum,unKillSoldierNum,unPlayerDeadNum,unFujiangDeadNum,unSoldierDeadNum,unHitPlayerAmount,unHitFujiangAmount,unHitSoldierAmount,unOccupyNum,unFJExp,unSoldierExp}, pvpHeroData{unKillNum,unDeadNum,unDmgAmount,unMaxOnceKillNum,unAssisstAttkNum,unFinalHitNum,unRescueNum}, rankLev, quizCoin}]`.
- `gameResult` (own result): `mode, subMode, teamIndex, beActHit, beActHitAdd, actHit, actHitDec, playerExp, soldierExp, exploit, basecoin, coin, prestige, fj1Exp, jade, fleecoin, actHitDecCoin, beActHitAddCoin, supplyArmyCostCoin, win, bmvp, bNegativeGame, bAbnormalState, bCheat, bHungUp, bMaliciousLogOut, surivialTime, battleTime, scoreLev, killplayerNum, hitInfo{nHitPartCount,nBeHitPartCount,nHitShieldCount}, weapons[{weapon, weaponHitNum, weaponDamage}], extraRewards[{value}], medalreward[], score, process, resultCode, resultParam, roomId, armyType, fj1Id, fightval, profitDetail[], isCurMatch, battleId, evaluate, ceVal, addceVal, isceScale, combatEff_scale[], addVal, rankScore, killScore, dmgScore`. Lua `GetGameResultInfo_Commom_lua(id)` fields map as: HaveWin=win, GameMode=mode, SilverCoin=coin, FJ1ID=fj1Id, GeneralExp=playerExp, FJ1Exp, StandardExp, SoldierExp, scoreLev, killPlayerNum, fleecoin, TotalPlayer.
- Frontend side (Login.lua 2356): `On_GameResult` first checks `TUTORIAL<4`; Tutorial / Crusade_Tutorial / Complete_Tutorial modes only reset the prepare state and show NO result screen. So for the training ground no gameResult is needed; the process exit (callback 322 `On_KnightClientClose`) returns to the lobby. A minimal safe push for the real modes would be `{"msgs":[{"mode":N,"subMode":0,"win":1,"coin":0,"playerExp":0,"soldierExp":0,"resultCode":0,"battleId":"1"}]}` (omit nested objects: the DLL indexes them, scalars there crash). Not implemented in the lobby (out of scope, no test possible).

## 5. Other findings
- eBattleMode passed to `ISyncClient::Create` (Kingdom `0xec3360`): by game class: KingdomTutorialSyncGame 0, KingdomTaofaTutorialGame 4, PVP_DaTaoSha 0x13 (the "DTS player" branch of ControlAiPlayer `0x1000b2e0`), others 1/2/3/5-0xf/0x10/0x12/0x15; KingdomChallengeGame (gameMode 5) is not one of the checked names -> probably default 1 [M]. So ControlAiPlayer goes through the normal AI manager (`this+0x68`, `0x10005e60` -> `ai::AIPlayer` ctor `0x100ff540`, signal connections only; no config read seen in the ctor).
- `config\botnames.txt`/`botequip.txt` are NOT in config.cfg (server side only).
- Troop SoldierKind -> UE3 spawn class `[0x33]`: 1 foot, 2 archer, 3 cavalry, 4 horse archer (soldiers.txt `SoldierKind`).

## 6. Open questions (ranked)
1. Does the hero appear/become controllable with 7? Which Reqs come after (SelectBornPos? TutorialStep)?
2. Position/orientation and equipment slot semantics beyond the log-string slots ([0x4b], [0x4e-0x55], [0x22],[0x23],[0x24]); spawn point for map 17 (UE3 level PlayerStart vs DataSet).
3. Troop/AI path: where the UE3 AI spawn `0x00e6b2d0` is called from, and whether `ControlAiPlayer` (0x4e4a) and the Control* ids 0x4e46..0x4e4e do what the RTTI chain suggests.

