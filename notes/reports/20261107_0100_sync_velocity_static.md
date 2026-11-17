# SyncVelocity / SyncAccelerate / ground-walk static study + ue_inspect option 6 (11-07)
Inputs: in-game ue_inspect (holding W): aForward 0 in 32/33 (one sample 857), RawJoyUp 1.0, Pawn.Acceleration const (-2601,1493,0), Velocity 0, Physics Walking, SyncVelocity/SyncAccelerate 0.

## 1. Script (KingdomGame_plain.u; tools\work\hits_sync.txt, hits_af.txt, d5\, d6\)
- SyncVelocity, SyncAccelerate: **zero references in any script function body** (sc.exe scan of all UFunctions). Only native touches them. bLockSpeed: script only (KingdomPlayerInput.PressForward/PressBackward/PreProcessInput, KingdomSyncPawn.DealWith*Stall/CancelLockSpeed, KingdomHorse) -> it gates keys, not ground physics; hero value is 0 anyway.
- SyncAccelerate is a 12-byte member (+0x1D28..+0x1D34, between SyncVelocity +0x1D1C and SyncID +0x1D34): same size as a Vector (3 floats) = likely Vector (verified size from the property offsets, type itself hypothesis).
- Controller chain: KingdomChallengePlayerController -> KingdomSyncPlayerController -> KingdomPlayerController. Natives on KingdomSyncPlayerController: ReplicateMoveToSync, ForceReplicateMoveToSync, GhostReplicateMoveToSync (exec thunk 0xd68270 -> vfunc +0x74c), SyncReqXxx; KingdomSyncPawn natives: SmoothLocation (thunk 0xd6b1b0 -> vfunc +0x654), SmoothRotation, DragSyncPawnToGround, GetPlayerAccelRate (0x7d4680).
- KingdomPlayerController.PlayerWalking.PlayerMove: if Pawn.Weapon==none -> Engine PlayerMove; Push/BreakShield/StandUp weapon states zero Velocity+aForward; Sprinting states use accel = Vector(Pawn.Rotation)*GetPlayerAccelRate() then ReplicateMove/ProcessMove; else Engine PlayerMove.
- KingdomSyncPlayerController.PlayerWalking.ProcessMove: Health>1 and normal walk -> plain `super.ProcessMove` (Engine, local movement; **no ReplicateMoveToSync**); only the DTS crouch/prone (nWalkStyle_DTS>0) and Health==1 cases do `Pawn.Acceleration=newAccel; ReplicateMoveToSync(...)`. So ground walking is local UE physics; the Sync move requests are sent by native code when the pawn actually moves (consistent with: W sends nothing because Velocity stays 0).
- KingdomPlayerInput.PlayerInput: `aForward += aBaseY` (aBaseY = RawJoyUp*100*dt*MoveForwardSpeed). 857 = 1.0*(100*0.00714)*1200 -> the input pipeline DOES compute aForward for W. The gate block (GRI==none || !bMatchHasBegun || IsMoveInputIgnored -> zero) is patched out in the installed KingdomGame.u (md5 71bc9030... = server\mods\KingdomGame_A.u, verified). Because aForward is also consumed/cleared inside the frame, the sampled 0s do NOT prove it is zeroed.
- Key arithmetic (hypothesis, strong): Acceleration magnitude sqrt(2601^2+1493^2)=2999 = AccelRate 1000 x ReplicatedMovementSpeedModifier 3.0 (both read from the hero: AccelRate 1000, ReplicatedMovementSpeedModifier 3.00). A constant non-zero Acceleration while W is held is exactly what PlayerMove produces with a working W. => input and PlayerMove work; the PAWN does not integrate velocity on the ground (Velocity 0, Physics Walking). Air drift/jump works (velocity from jump).

## 2. Native (Win32 exe, private project tools\ghidra_projects_c, copy of Kingdom-Win32 + Sync(Client).dll)
- Exec tables: 8-byte (name,fn) entries at 0x1602300.. (SyncPawn) and 0x1602660.. (SyncPlayerController); helper tools\work\dump2.py <addr> <n>.
- All Kingdom natives are thunks that pop script args and call a virtual (+0x74c ReplicateMoveToSync, +0x654 SmoothLocation); I could not identify the KingdomSyncPawn / SyncPlayerController vtable in the time box (vtscan.py gives ambiguous matches), so the actual code that decides to clamp Velocity / write SyncVelocity and the sender of 0x2738 is NOT identified (previous report also failed on this). No server Cmd was found that writes SyncVelocity/SyncAccelerate; msg layouts of 0x4e50/0x4e51/0x4eca remain "same as 0x2738/0x2739/0x2721" from codec sharing (hypothesis).
- Next static step: on Win64 (or Win32) find who READS offset +0x1D1C (Win32 offset differs): Ghidra search for `fld/movss [reg+off]` with the Win32 offset (compute from Pawn field order) inside KingdomSyncPawn::Tick/physWalking; or break-on-write with Cheat Engine on hero+0x1D1C while jumping.

## 3. Tool: ue_inspect option 6 (--exp)  [selftest + py_compile only, NOT run in game]
- Asks speed (default 3.0) and what to write: 1 SyncVelocity=(v,0,0) (default), 2 SyncAccelerate, 3 both, 4 direct UE Velocity (x100). Re-writes every 20 ms for 5 s, prints every 0.5 s: Location, Velocity, SyncVelocity, SyncAccelerate, Acceleration, plus Health/Physics. Writes 0 back at the end. Needs admin (write). Saved in server\logs\pawn_probe_last.txt.
- Axis: sync coordinates have y vertical, x forward-ish (report 1900); x is used. Mode 4 is the control: if even direct Velocity writes make Location move, the pawn does integrate and something clamps Velocity each tick; if Location does not move at all, the pawn's tick/physics is frozen on the ground (e.g. not "ticking", bMovable off, ground-follow to sync unit position).

## 4. Variant 33: NOT written
No evidence for a server message that sets ground velocity; V23 shows relaying 0x4eca/0x4e50 is harmful; layouts unproven. Waiting for option 6 result.

## 5. Reading option 6 results
- Mode 1/3 moves Location -> SyncVelocity drives the ground pawn; some native/sync msg normally fills it (the sync unit state); next: find that message (slave unit move or Cmd). 
- Only mode 4 moves it -> UE velocity ok, native overwrites Velocity from SyncVelocity each tick; SyncVelocity must be fed by the sync unit (server must move the WalkerSlave).
- Nothing moves -> pawn physics frozen: look at Physics volume / bMovable / "Pawn.Controller state" etc.
Dead ends: sc.exe scan for SyncVelocity in scripts (0 hits); vtable scan of Win32 exe.
