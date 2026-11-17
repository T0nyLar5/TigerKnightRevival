# Pinned hero position: lockstep hypothesis, native study, variants 33-36, ue_inspect opt 7 (11-07)
Input: opt 6 mode 4 (UE Velocity=(300,0,0) every 20 ms, 5 s): Location x 100.10 -> 100.17; SyncVelocity writes do nothing; jump (vertical) works.

## 1. Is the sync sim waiting for frames? (mostly NO)
- battle_server.py frame_loop already sends MsgFramework 0x2715 every 50 ms from connect (empty frames included), so frames/frame numbers advance. A "periodic empty frame" variant would be identical to V30; not built.
- Sync.dll SyncSlave vtable 0x1012a154 (read with tools\work\vt.py): +8 = frame sink 0x10033bf0: deserialize+dispatch payload msgs (0x100344e0 -> 0x100348c0), store frameNo at this+0x154, call UE3 callback (+0x174 vtable+0x50)(frameNo), then iterate all units calling unit->vtable+8(world) (0x100391a0) = one sim step per received frame, step = Sync config +0x28 (50 ms default, 0x1000a370). 0x10021060 is only the "./synclog" debug dump. So the sim does advance with our frames; whether a unit moves depends on its current Act (see 3).
- 0x4e20 CmdSync (SyncClient 0x100b41c0, uVar1==20000): calls slave vtable+0x50 = 0x10001010 which is an EMPTY function (verified), then sets SyncClient[0x26]=1. So CmdSync carries no world snapshot the slave uses; it only sets a synced flag. Sending it stays unnecessary/harmful (V13).
- Other top-level types 0x4e22/0x4e23/0x4e52/0x4e80/0x4ecc have SyncClient handlers; everything else is re-serialized to slave vtable+0x5c = 0x10034610 = forwards to UE callback +0x3c (not the sim).

## 2. Who writes the pawn Location? NOT FOUND (time box)
- Kingdom natives are thunks into unidentified vtables (SmoothLocation thunk 0xd6b1b0 -> vfunc +0x654; no RTTI in the exe). Location of the writer still unknown. Candidate explanation (hypothesis): KingdomSyncPawn native Tick snaps horizontal Location to the sync WalkerSlave unit (SmoothLocation) while vertical comes from UE physics (jump works). Then walking = the sync unit must move: input -> ReqMoveActionStart -> master -> Cmd; our server is the master and sends nothing.
- Suggested dynamic check: Cheat Engine "find what writes" on hero Location.x (Win64) while standing; or compare hero Location with the slave unit position (no tool yet).

## 3. Slave walker messages (Sync.dll, new, layouts hypothesis H)
- Dispatcher 0x100348c0: per-unit ids; WalkerSlave (RTTI) handles 200 (seek/move-to), 0xc9 (MSG_FOLLOW target uid), 0xca (stop/ActWalkerBreak), 0xcb, 0xcc, 0xcd...; 400 other walker op. Casting a non-Walker unit to WalkerSlave gives NULL and the handler would crash (unknown whether a kind-1 Player unit is a Walker).
- Msg 200 body (deserializer 0x1003c9c0): uvar uid | f16 x5 (target x,y,z, +2 unknown) | bool | f16 | f16. Handler FUN_1005a500(&f16s, bool, f16 -> unit+0x100 when bool, f16 -> state+0x238): creates ActWalkerSeek unless the unit is in a blocking act (acts 6,0xd,0xc,0xe,0x10,0xf,0x11); likely bool = use custom speed, first f16 = speed (m/s). Guess only.
- Registry of ids/serializers: Sync.dll init 0x100450e0 (pairs ser/deser per id; 200 -> 0x1003ca60 creator, 0x1003c890 serializer).

## 4. Variants (all UNTESTED; base = V30 incl. valid spawn, V28 re-countdown at +8 s, move test at +10 s)
- V33: Cmd 0x4e50 (uid, mode 1, f16 vel (4.5,0,0)) every 500 ms for 10 s, then 0x4e51 End. Velocity units/layout from real 0x2738 logs (jump = mode 2, vel (0,6,0): `91 4e 02 00 00 00 46 00 00`).
- V34: Cmd 0x4eca (uid, f16 x,y,z) every 50 ms, x advancing 4.5 m/s from the spawn point, 10 s (log every 10th).
- V35: V33 + V34, 15 s.
- V36: in-frame slave msg 200 toward spawn+30 m, 5 times 2 s apart. May crash the game if the hero unit is not a WalkerSlave.
- Test order: 33, then 34, then 35, then 36 (crash risk last). Success = hero slides or Location x changes in ue_inspect opt 4. Server log lines "V33 WALK" / "SEND v33 ..." prove what was sent.
- Rationale: V23 showed the client applies 0x4e50/0x4e51/0x4eca to the local pawn; V26 sent velocity 0 (no effect expected), never a non-zero velocity.

## 5. ue_inspect option 7 (--time, read only; selftest OK, not run in game)
Prints hero flags (Dilation, Base, bHardAttach, bMovable, Role, Physics...), WorldInfo dilation/TimeSeconds props, then samples WorldInfo.TimeSeconds and Location for 3 s and prints the time ratio (about 1.0 = no dilation). Launcher 英雄速度檢查.bat key 7.

## Dead ends
Searching Kingdom exe for SmoothLocation implementation (no RTTI, ambiguous vtables, again); frames-only variant (already the baseline).
