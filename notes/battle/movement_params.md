# Movement-related parameters (survey 2026-11-07 12:00)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Legend: V = value seen live in game (verified, from HISTORY/reports), D = class default (tools\work\cls), S = static reading (hypothesis). "key I" = writable in a preset (see reports\20261107_1200_movement_presets.md).

## Hero pawn (KingdomSyncPawn -> KingdomPawn -> Pawn)
| field | live (V) | default (D) | why it may matter |
|---|---|---|---|
| GroundSpeed (Pawn) | 450 | 450 = NormalRunSpeed | ground max speed; native GetPlayerAccelRate (Win32 0xdb90d0, S) re-sets it each call from NormalRunSpeed/QuickRunSpeed. Creep 0.04 UU/s = 450 x 1e-4 |
| AirSpeed / WaterSpeed | not logged | | jump drift works, so probably not the gate |
| AccelRate (Pawn) | 1000 | 1000 | Acceleration = AccelRate x RMSM = 3000 while W (V): input path is OK |
| ReplicatedMovementSpeedModifier / MaxModifier | 3.0 / 3.0 | 3.0 | script scale; not 0 (V) |
| NormalRunSpeed / QuickRunSpeed / QuickRunSpeedWithGroundOnlyEquip (config) | 450 / ~540 / - | ini 450/530/550 | source of GroundSpeed; P4 raises them |
| PlayerStalls, bLockSpeed, bSlowDown, bSlowMove_DTS, bTurnSlow, bLockLocation | all False/0 (V, key A) | | slow/lock flags ruled out |
| Physics / LandMovementState | PHYS_Walking / PlayerWalking (V) | | ok |
| Velocity / SyncVelocity / SyncAccelerate | 0 / 0 / 0 while W (V) | | symptom: ground Velocity never built |
| Location vs LastValidServerLocation, TooFarFromServerLocationTime | creep only; key B pin no effect (V) | | server-position pull-back ruled out by key B |
| Mesh RootMotionMode | RMM_Ignore (V, key E); BlendBySpeed Speed=0 | | root motion not the mover; no anim is a symptom |
| JumpZ | 600, jump works (V) | 600 | air movement fine |
| CustomTimeDilation / world dilation | key 7 read-only | 1.0 | P5 writes 1.0 |

## Controller (KingdomChallengePlayerController -> KingdomSyncPlayerController -> KingdomPlayerController)
| field | live | default | note |
|---|---|---|---|
| fPersonToSelfMaxSpeedFactor +0x7A8 | 0.00 (=1e-4), re-zeroed by the game per tick (V, key G) | 1.0 (D) | native writer FUN_140aed840 @0x140aee765 = max(DataSet f32[0x26], 1e-4) (S) |
| fPersonToHorseMaxSpeedFactor +0x7A4 | 0.00 or 1.0 (V); stays when written | 1.0 | writer @0x140aee73f = max(DataSet f32[0x27], 1e-4) (S) |
| fForward/Back/Right/LeftSpeedFactor (+WhenHold) | 1.0 / 0.6 / 0.9 / 0.9 (V, key F) | no default | ruled out |
| fSpeedAttenuationFactorOnGround / OnHorse | not logged | 1.0 / 2.0 (ini 1.5) | native only (no script reader); meaning unknown |
| fAccelAttenuationFactorOnGround / OnHorse | not logged | 0.2 / 1.2 | same |
| fMaxSpeedAttenuationValueOnGround/Horse, fMaxAccelAttenuationValueOnGround/Horse | not logged | 80/180, 15/80 | same; P5 writes the Ground values 0 |
| fPlayerMoveStrafeSpeedFactor, fPlayerTurnSlowSpeedFactor | not logged | 0.5, 0.5 | strafe/turn slowdown; P5 writes 1.0 |
| bIgnoreMoveInput / bIgnoreLookInput | False (V) | | input not ignored |
| aForward (PlayerInput) | 857 once, else 0 (V, sampled) | | |

## Game objects
- KingdomChallengeGame (PlayMode TUTORIAL, CurrentStage GEDANG): bTimerCountDown True (V); IsChallengeEnd/IsPlayerChoosing cleared by key F (no effect, V). KingdomGame bGameReady False (V) - never written in any test before key I.
- GRI: bMatchHasBegun True, ElapsedTime 15, TimeLimit 0 (V). bStopCountDown: native only.

## DataSet (local player; native FUN_140aed840 Win64 @0x140aed840)
- Accessor: `DAT_14195f320->vtable[+0x28]()`; int getter vtable[+8](idx); float getter vtable[+0x18](idx). Read at spawn: ints 2,3,0x4b,0x18-0x1b,0x4e...; floats 0x27 -> controller +0x7A4, 0x26 -> +0x7A8, each max(x, 1e-4) (S; constant 0x14119ffd4 = 9.99999747e-05).
- Encoding: float slots are raw f32 bits inside the u32 array. Evidence: Win32 SyncClient DataSet SetFloat (vtable slot 4, 0x10022f20) stores the float bits unchanged at array[idx] (idx u16, bounds-checked vs N); pos slots [9],[10] use the same encoding (battle\variants_7_9_recheck.md).
- Memory: heap copy of N x u32 per PlayerCtl (ctor 0x100cbf10 Win32). Key I finds copies by the gear-id signature at slots 0x18..0x1b (17000011, 17100001, 17200001, 17300001) and writes [0x26],[0x27]=1.0f.
- No other writer of controller +0x7A4/+0x7A8 found by scanning the Win64 exe (only class-default struct copies at 0x140a81dac / 0x140a4c472, S). The per-tick re-zero seen live suggests FUN_140aed840 (or a caller) re-runs, so a DataSet value, not a one-off controller write, is the right lever.

## 1e-4 floors (constant 0x14119ffd4)
- Shared constant, about 240 byte references in .text (mostly mis-decoded); 25 real comiss sites: 0x140093004 0x14027d78a 0x1403e8cd9 0x140463158 0x14048ed90 0x14048ede3 0x14048f2ca 0x14048f338 0x1404e85b8 0x14054bf1b 0x1405c74de 0x140647e6c 0x1406488b1 0x1406507f1 0x14065a38e 0x140682310 0x14068231f 0x1406823a2 0x1406d0a28 0x14070e362 0x140711b4c 0x140712068 0x14072fc11 0x140803fcd 0x140bc750e. NOT classified (generic zero checks); only FUN_140aed840 stores into the controller. If key I fails: decompile these in tools\ghidra_projects_w64 and look for a GroundSpeed-based max().
