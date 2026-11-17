# Research: troops, part 4 (sections 7-8: unknowns, function index, UPDATE 2026-11-05 PM)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_troops.md](research_troops.md) (table of contents).

## 7. Unknowns / confidence
- Where in SyncClient the UE3 AI-spawn callback (`0x00e6b2d0`, cb vtable+8) is invoked: likely from the SoldierCtl/IPersonEvent when the slave AddPerson creates the unit (needs pos/dir which only the slave message carries) -- NOT proven (indirect call, not located). If nothing spawns: try 0x4e23 after the slave AddPerson, or 0x4e52 (same body).
- Whether `a` (not `kind`) is the terrain.cfg key (args shifted in decompile) and which ids besides 3 exist (terrain.cfg encrypted; loader `0x100b9060`).
- Meaning of DataSet 2,3,0x1e-0x22,0x3f,0x43,0x47 and classes beyond 1..4. Type ids of ControlSoldiers etc.
- Confidence: wire layouts H; owner requirement [0x32] H; class [0x33] 1..4 H; that section 6 yields a visible squad M-L.

## 8. Function index
Sync.dll: 0x10034630 (slave creation dispatch), 0x10033d40/0x10038620 (AddCreature), 0x10033e40/0x10038810 (AddPerson), 0x10038a00 (AddBullet), 0x10033f40 (DependOnAdd), 0x10021430 (agentType lookup), 0x100658a0 (copies 0x44 bytes of config; NULL crash), 0x100204d0 (loads terrain.cfg).
SyncClient.dll: 0x100b41c0 (top-level dispatch), 0x100afdc0 (0x4e23), 0x100afeb0 (0x4e52), 0x100619c0 (serializer), 0x100ec5b0 (creature-type switch), 0x100ec7f0 (SoldierCtl, vtable 0x10223cbc), 0x100d0180 (owner = DataSet[0x32]), 0x100d0d00 (uses DataSet[0x35]).
Kingdom exe: 0x00e6b2d0 (AI pawn spawn, cb vtable 0x0150fd18+8), 0x00e2ce00 (OnSyncSpawnAI wrapper).

## UPDATE 2026-11-05 PM
agentType key = agentparam.txt `type` (0 player, 1 soldier, 2 horse, 4 boss, 5 lieutenant); terrain.cfg only holds navmeshes. Soldiers: slave kind=1, a=1 (not 3). DataSet[0x33] = soldiers.txt SoldierKind (1 foot .. 4 horse archer); real ids e.g. 112011 (gear in research_free_1105.md). Implemented as variant 8.
