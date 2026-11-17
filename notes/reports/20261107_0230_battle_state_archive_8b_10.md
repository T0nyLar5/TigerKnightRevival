# battle_state.md sections moved out on 11-07 (detail archive)
Moved from notes/battle_state.md to keep it under 10k chars. Content unchanged.

## 8b. Variants 17-20 (walking gate)
- **18** (16 + Init(7) + slave AddPlayer(hero, pos 0), echo kept) TESTED: jump + attack, cannot walk, no duplicate hero. **Best base.**
- **19** TESTED 11-05: attack/block/jump OK, cannot walk, drifts in air. (18 + DataSet slots filled, on foot, via `hero_gear()` / `GEAR_FOOT_FULL`): [0x4e],[0x4f]=1021,1022 (armytype 112011 skilltype1/2), [0x4c]=15710100 (soldiers.txt nFlagId), [0x56]=1, [0x4b]=100 (Energy). Untested.
- **21** TESTED 11-05 20:57 (log battleserver_20261105_205712): countdown OK, W/D on ground send NOTHING (only SelfPing 5 s; mouse -> 0x2754 ~10/s), JUMP works and reports.
  - Decoded senders: 0x2737 ReqPosition = uvar uid, f32 x,y,z; 0x2738 MoveActionStart = uvar uid, uvar mode (1/2), f16 x3 vel; 0x2739 End = uid, mode; 0x2721 ReqMove = uid + f16 x3. Jump works (unit_default.ini loaded); ground block is in Kingdom (input -> velocity).
- **23** (21 + relay 0x2738->0x4e50, 0x2739->0x4e51, 0x2721->0x4eca, same body) TESTED: hero can NOT move and can NOT jump. **INSIGHT: the client DOES apply server Cmd move msgs (0x4e50/51/4eca) to the local pawn** (echo broke jumping). So movement may be server-driven/lockstep; never echo.
- **24** (21 + DataSet dir slots [5,6,7] = (1,0,0) f32) TESTED: attack, block, jump OK, cannot walk on ground. **Current base.**
- **25** (24 + at +8 s server sends Cmd 0x4e51 MoveActionEnd uid mode 1 and 2, no echo) and **26** (24 + at +8 s Cmd 0x4e50 Start uid mode 1 vel 0,0,0, then 0.3 s later 0x4e51 End). UNTESTED, scratch OK. Guess: clear a stuck move state. 25 suggested first.

- **25, 26** TESTED: cannot walk. **27** (24 + at +8 s BattleStart + countdown (3,0)(2,0)(3,0)) and **28** (same with (1,0)(2,0)(3,0)): TESTED 11-05 late, HUD and sound appear, still cannot walk. Static finding (notes\battle\walk_gate_v27_mod.md "Native findings"): GRI+0x1cc bit 0x2 = bMatchHasBegun is set only by native fn 0x753e10 when bStopCountDown (script KingdomSyncGame.MatchInProgress.Timer) is set; no Sync Cmd sets it directly.
## 10. V29 troops + AI enemy + end (11-06, UNTESTED; needs walking first)
- V29 = V24 + at +5 s 3x 0x4e23 (owner [0x32],[0x35] = hero, [0x33]=1, [0x3f/0x43/0x47]=112011 guess) then slave msg 3 (kind 1, a 1); +6 s enemy uid 30001: 0x4e22 isSelf=0 camp 0 -> slave AddPlayer -> 0x4e80 -> 0x4e4a; +150 s 0x4e73(1) + slave 9.
- Script (KingdomGame_plain.u): KingdomSyncGame.PostBeginPlay creates teams 0, 1, 255 only; OnSyncSpawnAIPlayer(pos,R,TeamIndex,Weapon[5],Helmet,Shawl,Armor,Shoes,Flag,Face[26]) puts a KingdomSyncAIPlayerController into GRI.Teams[TeamIndex] -> enemy camp 0 (camp 2 = no such team). OnSyncSpawnAI(pos,R,Team,BotType,SoldierID,Weapon[5],flag,fashion) = soldier; SoldierID via soldiers.txt (slot unknown).
- End: native calls script OnSyncEndGame(Result): 1 local win, 2 lose, else TimeLimit -> EndGame -> flash OnEndGameShowTabUI; tutorial game quits after 6 s. Triggering Cmd unproven (guess 0x4e73 = Result). Frontend result needs lobby push gameResultGlance/gameResult (training shows none).

