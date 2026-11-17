# Battle: countdown, battle start/end, results, configs (split from battle_state.md, 2026-11-08)
> rev 2 | 2026-11-08 02:22 | spawn-point picker (0x4f03/0x2792/0x2796) hypothesis recorded, no variant

## 5. Countdown, BattleStart, BattleEnd, results
- CmdCountDown(state, value) -> Kingdom 00ebfb00: 1 = prepare (freeze, timer UI); 2 = tick (value = seconds left; 0 = unfreeze); 3 = running. Used: (1,3)(2,3)(2,2)(2,1)(2,0)(3,0), 1 s apart. Ignored without hero, GameEngine and local controller.
- BattleStart = slave msg 8. BattleEnd = slave msg 9 in a frame, optionally with top-level 0x4e73.
- bMatchHasBegun (GRI+0x1cc bit 2) is set only by native 0x753e10 when bStopCountDown is set; no Sync Cmd sets it.
- Spawn-point picker (owner video 2026-11-08, H): real flow is countdown -> S>C CmdShowBornPos 0x4f03 -> C>S ReqSelectBornPos 0x2792 / Confirm 0x2796 -> S>C 0x4f04 / 0x4f08 -> ReBorn 0x4e80 at the chosen point. We send 0x4e80 immediately, so it never opens. Bodies undecoded; see reports\20261108_0222_prebattle_troop_select.md.
- Results: the UE3 exe never reports to the lobby. The frontend reads lobby pushes `gameResultGlance` / `gameResult` (omit nested objects). Process exit returns to lobby. Not verified in game yet.

## 6. Configs, maps, key functions
- Configs: notes/decrypted/cfg/ (tools/cfgdec.py; row 1 names, row 2 types, data from row 4). Map ids: notes/map_ids.md (17 = training ground).
- Key functions: SyncClient 0x100afab0 / 0x100b00b0 AddPlayer/ReBorn, 0x100afdc0 AddCreature, 0x100af840 Framework; Sync.dll 0x10034630 slave dispatcher; Kingdom 0x00e19260 / 0x00df26b0 pawn spawn, 0x00ebfb00 countdown.
