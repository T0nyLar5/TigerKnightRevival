# Movement presets (key I) + V37 check (2026-11-07 12:00)
## Done
- Survey: notes\battle\movement_params.md (hero/controller/game/GRI fields with live values, DataSet slots, 1e-4 floors).
- Key I / `ue_inspect.py --preset` (英雄速度檢查.bat; menu text server\text\probe_menu.txt): 5 cumulative presets, written every ~10 ms for 10 s while W is held; prints Location every 1 s and horizontal distance; then asks y/n for 60 s free walking; finally restores every original value (raw bytes saved before writing).
  1 = speed factors (controller Self/Horse 1.0, 8 direction factors normal) + DataSet[0x26],[0x27]=1.0f in game memory (found by gear-id signature);
  2 = 1 + challenge/match flags (IsChallengeEnd, IsPlayerChoosing, bTimerCountDown False; bGameReady, bMatchHasBegun True; bIgnoreMove/LookInput False);
  3 = 2 + LastValidServerLocation=Location, TooFar timer 0, bSlowMove_DTS/bTurnSlow/bSlowDown/bLockSpeed/bLockLocation False;
  4 = 3 + NormalRunSpeed 900, QuickRunSpeed (+GroundOnlyEquip) 1000, GroundSpeed/AirSpeed 900, AccelRate 4000, RMSM/MaxModifier 3.0;
  5 = ALL ON = 4 + Ground max attenuation values 0, strafe/turn factors 1.0, CustomTimeDilation 1.0.
  Missing fields are skipped and listed. No duplicate/conflicting writes (selftest asserts). Offline selftest OK (mock); NOT run in game.
- DataSet location: local DataSet = `DAT_14195f320->vtable[+0x28]()` (FUN_140aed840); the memory copy is the PlayerCtl N x u32 array, found by signature (no pointer chase).

## V37 check (server\battle_server.py)
- Slot 0x26 -> Self (+0x7A8), 0x27 -> Horse (+0x7A4): correct. Encoding raw f32 bits (P.f32bits): correct, same as pos slots [9],[10]; Win32 SetFloat stores float bits unchanged (SyncClient 0x10022f20). Static only (the Win64 getter itself was not decompiled).
- BUG FIXED: V37 put 0x26/0x27 only in the CmdAddPlayer DataSet, but the hero ReBorn (0x4e80, +450 ms) sent GEAR_112011 (zeros). ReBorn builds a fresh ctl with its own DataSet copy (SyncClient 0x100ee480 allocates a new 0x1b0 object), so the zeros could replace it before the local pawn spawn reads the DataSet. V37's ReBorn now uses hero_gear() (also carries pos [9],[10] and dir slots like AddPlayer). py_compile OK; battle selftest not run (rule).
- Test V37 together with key I? Yes, in two stages: start V37 alone and press W (no memory write); if it still creeps, run key I 5 in the same game. P1 writes the same DataSet slots into memory, so V37 and P1 test the same hypothesis by two routes.

## Test steps for the user
1. Run 英雄速度檢查.bat as admin only AFTER the hero stands in the battle (opening it earlier sent the game back to login). Press I, then 5 (all on). Enter, switch to the game, hold W during the 5 s countdown and 10 s. Note the printed horizontal distance.
2. If > 100: rerun with 1,2,3,4 to find the minimal set. If ~0: answer y to the 60 s free walk and try W, Shift+W, jump; report.
