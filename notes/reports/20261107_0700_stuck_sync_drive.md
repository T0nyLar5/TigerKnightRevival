# Key D (drive stuck sync copies), option-5 bool decode, bSlowMove_DTS static (11-07 07:00)
Status: code written + offline `--selftest` OK. NOT run in game (hypothesis until user tests).

## Key D (`英雄速度檢查.bat` D = `tools\ue_inspect.py --stuck`, needs admin)
1. Scan like key C (hero standing; copies of Location in f32/f64 UU+metres, int x1000/x10000/x65536, xyz and x,up,y orders; hero object excluded).
2. User jumps/runs far once (6 s). `narrow()` keeps ONLY copies still at the old position ("stuck"); copies that follow the hero are dropped. Aborts if hero moved <3 UU.
3. Prints up to 12 stuck candidates + for up to 6 of them a 64-byte neighbourhood (-24..+40 bytes, dwords; floats shown as `+off:fVALUE` when plausible else hex; zeros omitted) = look for velocity/speed/state fields of the sync unit.
4. Drive 10 s every ~10 ms (user picks candidates; sub-mode 1 / 2 / 3 = both, 10 s each, each with its own 5 s countdown, hold W):
   - 1: write candidate = hero's current Location (converted into the candidate's own unit/axis order by cand_write).
   - 2: candidate = start + dir*4.5 UU per tick; dir = hero Acceleration (horizontal, unit) if non-zero, else Rotation yaw (65536 = 360 deg).
5. Output: hero Location each second; start->end x/y change; per candidate "overwritten by game N times" (value != what we last wrote); list of candidates that drifted by themselves between the narrowing and the drive start; after the drive, neighbour dwords that changed (excluding the xyz triple).
Log: server\logs\pawn_probe_last.txt.
Reading: hero x/y big change = sync unit found/drive works. Overwrite 0 and hero unchanged = nobody reads these copies (dead/stale). Overwrites >0 = game writes them. Neighbour changes while we write = engine reacts (velocity/state fields).

## Option 5 / key A bool decode
`Walker.val` now decodes BoolProperty via BitMask (`boolv`, `learn_bm`): shows `True`/`False` (raw dword fallback `0x..?` if mask unknown). Option 5 lines for bools also print `(原始 0x..)`. Key A (`--speed`) now appends `bool_listing`: bools of hero AND controller whose name matches Slow|Stall|Lock|Move|Turn|Stun|Freeze|Block|Ignore|Stop|Drag|Walk|Run|Sync|Fall|Down|Dead|Stagger|Action (True first, max 45 each) -> includes bSlowMove_DTS, bTurnSlow, bMoveLocked, bIgnoreMoveInput, bInSlowKillAction...
Selftest asserts bMoveLocked decodes True and bBlockActors False (raw 0x5).

## Static: bSlowMove_DTS / bTurnSlow (verified from decompiled class dumps tools\work\cls\*.txt, 4 classes)
- Declared `var bool` in KingdomPawn (bTurnSlow, bSlowMove_DTS; plus bSwimming, bInLostControlState ...). They appear NOWHERE in any decompiled function body of KingdomPawn / KingdomPlayerController / KingdomSyncPawn / KingdomSyncPlayerController (grep: only the var lines). So script never sets or reads them -> native-only (set/read by exe/Sync code). Other .u classes were not dumped (not checked; raw name-index scan of the 228 MB plain.u is too noisy to conclude).
- Related config (hyp.): KingdomSyncPlayerController fPlayerTurnSlowSpeedFactor (UC default 0.5, unit_default.ini 1.0 "turn too large slow factor") and fPlayerTurnSlowAngle (default 0.5 / ini 0 "angle reaching turn slow") -> bTurnSlow is probably the native flag "turned more than Angle -> speed *= Factor". fPlayerStand/Crouch/LydownSlowDownFactor (ini 0.8) = quiet-walk factors, also only var lines in script. With ini values Factor 1.0 / Angle 0 turn-slow cannot give zero speed.
- bSlowMove_DTS: name suggests DTS (unknown abbreviation) slow-move state; no script clue to its effect. Value must be read in game (key A/option 5 now decode it). Raw dword 0x8C23 seen earlier at +0x580 was not decoded (several bools share it).
- KingdomPlayerController uses Pawn.GetPlayerAccelRate() (native) at lines ~5887/6111 for newAccel; that native is where slow flags would act on movement (hyp.).
