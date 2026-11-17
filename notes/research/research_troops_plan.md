# Research: troops, part 3 (sections 4-6: other messages, config ids, proposed sequence)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_troops.md](research_troops.md) (table of contents).

## 4. Other candidate troop messages (not analysed; names from SyncClient RTTI strings, type ids unknown)
`MsgCmdControlSoldiers`, `MsgCmdRemoveControlSoldier`, `MsgCmdSyncFormation`, `MsgCmdChangeFormation(+Mass)`, `MsgCmdAiFormationMass`, `MsgCmdMaxSupplyArmyNUM`, `MsgCmdTroopMove`, `MsgCmdAttachToPlayer`, `MsgCmdAttachPlayers`, `MsgCmdAiPlayerSoldierSkill`, `MsgCmdControlHorses`. The registry has no names; the deserializer->RTTI map would give ids. Kingdom natives `GetPlayerSoldierNum`, `GetSoldiersInfo`, `AddTroops`, `RecruitTroops` suggest HUD/squad logic may also need ControlSoldiers / MaxSupplyArmyNUM.

## 5. Config ids / fallbacks
- Hero/soldier type ids from config.cfg (still encrypted) appear only as DataSet slots (hero [0x3e],[0x44],[0x49],[0x4a]; soldier 0x3f/0x43/0x47/0x1e-0x22 unknown). No fallback table seen: the spawn function only range-checks [0x33] (1..4).
- Only hard Sync.dll config dependency: agentType in terrain.cfg (crash if missing, section 3).
- Unknown 0x4e23 creature type: logged, no unit, no crash. Unknown owner [0x32]: soldier silently not added.

## 6. Proposed minimum sequence (one squad of N soldiers for hero H = 10001)
1. (existing) top-level 0x4e22 MsgCmdAddPlayer(H, isSelf=1) then 0x4e80 MsgCmdReBorn(H).
2. For i = 1..N (N = 3..5 test; S_i = 20000+i): **top-level 0x4e23** body = `uvar S_i | uvar 80 | 80 x u32`; DataSet[0]=S_i, [1]=1, [2]=1, [0x10]=hero camp (same as hero's [0x10]), [0x32]=H, [0x35]=H, [0x33]=1, rest 0. Send after step 1 was processed (a later tick).
3. In a frame (MsgFramework payload), per soldier **slave msg 3 AddPerson**(uid=S_i, kind=0, f0c=0, f10=hero's f10, pos = hero pos + offset (x + 2*i), dir = hero dir, **a=3**, b=0, c=0), 1-2 frames after its 0x4e23. No msg 2 for soldiers.
4. Maybe later: ControlSoldiers / MaxSupplyArmyNUM for the HUD, formation messages for movement.
Server guard: never send 0x4e23 twice for a uid (second is ignored with an error log).

Note: the `a=3` values in section 6 are superseded by the UPDATE 2026-11-05 PM (see research_troops_unknowns_update.md): soldiers use a=1.
