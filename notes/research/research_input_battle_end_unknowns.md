# Research: input and movement, part 3 (sections 4-5: battle end, unknowns, test hints)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_input.md](research_input.md) (table of contents).

## 4. How the battle ends and what the lobby gets
- Server-side recipe to end: send slave msg **9** inside a frame (and optionally top-level 0x4e73 MatchEnd with varint 0/1). The client sets its "battle ended" flag (+0x228); what UE3 does next (closing the process / showing a result) is NOT resolved: `+0x228` readers not traced.
- The UE3 exe does NOT report the result to the lobby (battle_launch.md section 3; consistent: no lobby route is referenced by the exe/SyncClient here). The result screen is produced by the **frontend**: lobby pushes `gameResultGlance` and `gameResult` (Lua callback id 105 `MainMenu_Fighting_On_GameResult`, `Login.lua:2356`), and when the UE3 process exits frontend raises callback id 322 `On_KnightClientClose` (`Login.lua:2530`, `Param.nParam1` = result id; calls `BattleEnding_ActionOpen(id)` = victory/defeat banner `BattleEnding.lua`). `GetGameResultInfo_Commom_lua(nParam1)` reads the stored result by id. Tutorial modes (`eMatchMode_Tutorial`) take a shortcut: `On_GameResult` with TUTORIAL<4 only completes the tutorial (`Login_TutorialMode_Force_Complete`) and shows no result screen.
- Routes the fake lobby should push when the battle ends (names from `Login.lua`/notes; payload schema of `gameResult` is NOT known and needs a DLL parser dump): `gameResultGlance`, `gameResult`. Client requests after: `matchHandler.leaveMatch` (route table #113) is the only match-leave route seen; `userHandler.getBattleProfitMultiInfo` (#208) for the profit panel.

## 5. Remaining unknowns
1. Whether any Req is mandatory for the pawn to leave a "waiting" state (e.g. SelectBornPos on the tutorial map). Only a real run shows it: look for `RECV [after spawn]` types.
2. Real contents of the 75-slot DataSet and whether `UserLoadingFinish` names match the player list; countdown requires hero first.
3. Slave unit-message ids (UMsgMove etc.) and `kind` values for AddPlayer (config tables encrypted).
4. UE3 reaction to OnBattleEnd (+0x228 reader) and the `gameResult` JSON layout.
5. Exact id-to-name table for generic-codec Reqs (noisy; see caveat in section 1).
## Test hints
Next run: log every C>S type after spawn (already done). Expect 0x2721 MsgReqMove as soon as the hero walks; if it appears the unit is controllable and no further relay is needed. To test the end: send slave msg 9 in a frame plus top-level 0x4e73.
