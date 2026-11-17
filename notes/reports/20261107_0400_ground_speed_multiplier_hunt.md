# Ground-speed multiplier hunt (11-07): no zero multiplier found; ue_inspect option 10 added
Scope: script (UELib decode of tools\work\KingdomGame_plain.u) + Win32 exe (private Ghidra copy tools\ghidra_projects_speed, gitignored). Native part is Win32 only (game runs Win64).

## Script (verified by decode)
- Hero speed scaling lives in `KingdomPlayerInput.PreProcessInput` + `KingdomSyncPawn.DealWithSlope/DealWithLazy/StepSlowDown/DealWithUp|DownStall/CancelLockSpeed`.
- ReplicatedMovementSpeedModifier (RMSM) is written by PreProcessInput: `= DealWithSlope(true)` (when bLockSpeed and not pressing forward; Modifier from PlayerStalls: 0 -> 0.0, 1 -> 1.0, 2 -> 2.4/2.6, 3 -> 3.0), clamped to MaxModifier (3.0). `PlayerStalls` is changed only by UpStalls/DownStalls (controller) -> DealWithUp|DownStall; CancelLockSpeed resets RMSM=3.0, PlayerStalls=0, bLockSpeed=false. Hero has RMSM 3.0 (= MaxModifier), bLockSpeed 0: script multiplier is NOT zero. StepSlowDown (bSlowDown) lowers RMSM by SpeedDecrement*dt to 0: candidate only if bSlowDown is set (not read yet).
- Walking accel: `KingdomPlayerController.PlayerWalking.PlayerMove`: newAccel = Pawn.GetPlayerAccelRate() * Normal(newAccel) (native).
- Script never writes GroundSpeed/AccelRate for the hero (only InitWithPawnInfo for AI soldiers, SI.MaxSpeed / fSoldierAccelRate). Hero GroundSpeed 450 = config NormalRunSpeed (KingdomGame.ini NormalQuickRunSpeed 450, QuickRunSpeed 530, ...Ground 550).
- Config vars with NO script reader (native only): KingdomSyncPlayerController fSpeedAttenuationFactorOnGround(1.0 default, ini 1.5), fAccelAttenuationFactorOnGround(0.2/0.5), fMaxSpeedAttenuationValueOnGround(80), fMaxAccelAttenuationValueOnGround(15/50) + Horse variants (ini lines 13-21 of notes\decrypted\cfg\frontend_config\config\KingdomGame.ini). Hypothesis: native "attenuation" of speed/accel; not proven to zero anything.

## Native (Win32 exe)
- `UKingdomPawn::execGetPlayerAccelRate` thunk 0x7d4680 -> virtual slot +0x420; KingdomPawn vtable 0x14da468, override **0xdb90d0** (hypothesis-level reading): sets Pawn.GroundSpeed (+0x288) every call from KingdomPawn config fields (+0x6b0 NormalRunSpeed, +0x6b4 QuickRunSpeed, +0x6b8 QuickRunSpeedWithGroundOnlyEquip; +0x6bc/+0x6c0 accel ints) depending on velocity/sprint flags, returns AccelRate (+0x298). Win32 offsets: GroundSpeed +0x288, AirSpeed +0x290, AccelRate +0x298. So GroundSpeed/AccelRate are NOT scaled to 0 there (matches in-game 450 / 1000).
- Other virtual slots 0x4a0-0x670 of that vtable are Kingdom overrides (0xdbeb10, 0xdaecb0, 0xdad460...); 0xdad2b0 = skeleton update-rate (not movement). Engine physWalking/CalcVelocity (0x91xxxx range) NOT identified; no RTTI in the exe. tools\ghidra_scripts\TkDecomp.java now creates a function when none exists at the address (many Kingdom functions were unanalysed).
- Not found: native reader of RMSM / attenuation vars; Win32 offset of RMSM unknown (property order in SyncPawn: SpeedIncrement, SpeedDecrement, MaxModifier, RMSM, ..., PlayerStalls is printed reversed by UELib).

## Server link (item 3)
- No evidence a DataSet attribute feeds ground speed: hero speeds come from config NormalRunSpeed (ini) and script defaults; DataSet slots read by the spawn code (see variants_7_9_recheck.md) are health/team/gear/pos. SoldierInfo.MaxSpeed (soldiers cfg col MaxSpeed, fujiang.txt) only reaches AI via InitWithPawnInfo. => variant 37 NOT created (no candidate attribute).

## Deliverable
- `英雄速度檢查.bat` key **A** (= option 10) / `ue_inspect.py --speed`: lists Float/Int hero fields matching Speed|Rate|Scale|Modifier|Mult|Factor|Weight|Slow|Stall|Lazy (max 40 lines, with offsets), then asks a property name, new value and y to write. py_compile + --selftest OK; NOT run in game. Run as administrator to write.

## Next (suggestions)
1. User runs option A while holding nothing: read RMSM, MaxModifier, PlayerStalls, bSlowDown(via 5 with filter "Slow"), SpeedDecrement; try writing GroundSpeed 900 / AccelRate 5000 to see if ground speed scales at all.
2. If speed stays ~0 whatever is written: the pawn position is pinned natively (LastValidServerLocation / TooFarFromServerLocationTime / DragSyncPawnToGround in KingdomSyncPawn) rather than a speed scale: add those fields to the option-A regex (use option 5 filter `Server|Drag|Pin`).
