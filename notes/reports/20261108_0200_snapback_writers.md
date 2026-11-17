# Snap-back writers (CE trace V37) decompiled, Win64 Ghidra (2026-11-08 02:00)
Source: CE trace, Location.X writers; Ghidra addr = 0x140000000 + exe offset. All below = static analysis (hypothesis) unless marked verified.

## 1. The four writers
- exe+4D09C4 (0x1404d09c4): inside FUN_1404d01b0 = UWorld::MoveActor (45 KB), the per-frame mover (965 hits). Not a teleport by itself.
- exe+4D0080 (0x1404d0080) in FUN_1404cfd60 = UWorld::FarMoveActor(world, actor, destVec3, bTest, bNoCheck, bAttached). Net teleport. 2 hits. ~55 callers; the Kingdom ones: FUN_140ae0370, FUN_140aec530 (both sync-object callbacks, below), FUN_140aed840 (hero spawn), FUN_140ae7b50, FUN_140b33380/b340f0/b40eb0/b42720 (other movers).
- exe+5AB6F3 / 5ABA9B (0x1405ab6f3 / 0x1405aba9b) = same function FUN_1405ab690 = MultiPointCheck(world, hit list, actor, location, extent, traceflags): it swaps actor Location/Rotation with the test location (swap in at 5AB6F3, swap back at 5ABA9B), runs the checks, restores. NOT a net move. Called in a loop (up to 5x) from FUN_140ae0370.
- So the hits are one chain: FUN_140ae0370 ran about twice: 4 swap pairs (MultiPointCheck) then 2x FarMoveActor = the snap-back (3 snap-backs seen, one probably before CE attached). Confidence about 65%.

## 2. The decision / target (hypothesis ~60-65%)
- Globals: DAT_14195f338 = local hero pawn; DAT_14195f340 = hero sync object (0x178 bytes, created in FUN_140aed840 at spawn; the Win32 DAT_01717060 twin). Fields: +0x14 xyz = "synced base position" (initial value from spawn point lookup FUN_140b78870), +0x20 xyz = working copy (+0x14 transformed by FUN_140b39470), +0x154 = some id, +0x10 = team?.
- FUN_140aaf020(pawn, vec3) = THE SETTER (Win32 FUN_00db5ef0): range check +-262144, pawn+0x454 (base/attachment) == 0, then obj+0x14 = vec, obj+0x20 = transform. Only reached by vtable (9 vtables, pawn classes); no direct call sites. If a pawn has +0x454 != 0 it writes a sub-object (+0x570) instead.
- FUN_140ae0370 (vtable slot at 0x1414b9318; sibling FUN_140aec530 at 0x1414b9248): obj+0x20 = obj+0x14 (+ hero Z offset), then up to 5x MultiPointCheck at obj+0x20 to push the hero out of overlapping actors, line-check to ground (FUN_1404c9b30), then FarMoveActor(pawn, obj+0x20). I.e. "put the hero at the synced position". Both are virtual callbacks of the sync-object class (vtable ~0x1414b9570); the caller (Sync.dll unit listener) was NOT traced.
- Resulting theory: something (likely Sync.dll "unit position vs reported position > leash" check, ~10 m) fires this callback; the target obj+0x14 stays at the spawn point because nothing calls the setter 140aaf020 with new positions. Not found: the distance check itself (the ~10 m constant) and who calls the setter. Distance constants seen elsewhere (250000 / 90000 / 40000 UU^2) are interaction ranges (FUN_140bb5060), not the leash.
- FUN_140b941c0 (NPC interaction) reads obj+0x14 too: obj+0x14 is also used as "hero position" for NPC picks, so it must normally track the hero.

## 3. Variant / experiment
- V44 NOT implemented: no server message identified that reaches the setter (it is a UScript/virtual-only path; the top-level Cmd 0x4eca and in-frame slave 401 both showed no reaction in V38-V42).
- Key J of 英雄速度檢查.bat (`ue_inspect.py --leash`): reads module base + 0x195F340 (obj) and +0x195F338 (pawn). Step 1 read-only: prints both pointers (pawn must equal the found hero = address check), hero Location, obj+0x14, obj+0x20. Decision data: if obj+0x14 sits at the spawn (about 0.5,-0.6 x100?) while the hero walks, hypothesis confirmed. Step 2 (y, admin): 60 s copy hero Location into obj+0x14 and +0x20 every 10 ms (restored after). Success = hero passes 12 m from the start without snap-back. Selftest (mock) OK, not run on the real game.
- Units caution: obj positions may be UU (like Location); if obj+0x14 looks 100x off vs Location, the writer should scale.
- If J fails: next static step = find the caller of the listener slot 0x1414b9318 (Sync.dll Win64 unit position callback) and the leash constant; or CE "find what accesses" obj+0x14 (obj address printed by J).
