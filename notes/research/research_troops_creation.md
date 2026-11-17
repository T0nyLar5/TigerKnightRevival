# Research: troops, part 1 (sections 1-2: creating the soldier Ctl, DataSet slots)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_troops.md](research_troops.md) (table of contents).

## 1. Top-level MsgCmdAddCreature 0x4e23 (creates SoldierCtl / HorseCtl / BossCtl ...)
- Dispatcher `0x100b41c0` -> `FUN_100afdc0` (SyncClient). Registry `0x10093050`: 0x4e23 (ser `0x10061cf0`, deser `0x10061a80` -> `0x100619c0`). **0x4e52 uses the same deserializer** (same body layout; handler `0x100afeb0`, not needed). [H]
- Wire body (uvar = LEB128) [H from `0x100619c0`]: `uvar uid | uvar N | N*4 raw bytes (the DataSet, N little-endian u32)`. No isSelf byte, no strings. Header as always `u16 len | u16 type`.
- `FUN_100afdc0`: looks up a `syncclient::IUnitCtl` by DataSet[0] (uid). **If one already exists nothing happens**; otherwise `FUN_100ec5b0` creates it. [H]
- `FUN_100ec5b0` switches on **DataSet[1] = creature type**: 1 = `SoldierCtl` (`0x100ec7f0`, size 0x188), 2 = Horse (`0x100ec950`, logs "AddHorse Id:%u"), 4 = `BossCtl` (`0x100ecaa0`), 5..0x1d (except 0x12) = other classes (not analysed); anything else logs "add unknow creature type[%u]" and creates nothing. [H]
- SoldierCtl creation: it calls its virtual +0xc4 (`0x100d0180`, vtable 0x10223cbc): it takes **DataSet[0x32] (byte offset 200) as a uid and looks that unit up; if not found it returns false and the soldier is NOT registered**. If found it stores the owner at ctl+0x184. So **DataSet[0x32] = owner uid = the hero's uid (the hero's PlayerCtl must already exist, i.e. 0x4e22 AddPlayer processed first)**. [H] On success the Ctl is registered with the unit manager via vtable +0x1c (uid, ctl) -- the table Sync.dll `0x10038810` later queries by uid for the unit event.
- DataSet[0x35] (offset 0xd4) is read as another unit uid in soldier code (`0x100d0d00`, and in the 0x4e52 handler when DataSet[1]==1): looks like "commander/leader uid". Set it to the hero uid too. [M]

## 2. DataSet slots for a soldier (read by the Kingdom spawn function `0x00e6b2d0`)
`0x00e6b2d0` is the UE3 callback that spawns an AI pawn (script event `OnSyncSpawnAI`, name at 0x014c2ce0, FName global 0x0170bea8, raised by wrapper `0x00e2ce00`). It sits in the FKingdomSyncCB vtable (base 0x0150fd18) at **+8** (ReBorn / spawn-remote-player is +4). thiscall, `ret 0x10` (uid, ?, float* pos, float* dir). It fetches the unit by uid (DAT_01717050 vtable+0x18) and reads its DataSet (getter = vtable+4, arg = index) [H]:

| index | use |
|---|---|
| 0x10 | camp/team -> pawn+0xc (same slot as hero camp) |
| 0x32 | owner uid (read; unused here) |
| 2, 3 | read into locals (hp/flags?) [L] |
| 0x33 | **soldier class 1..4** (switch; 1/2/3/4 stored to pawn+0x114; any other value -> returns 0 = **no pawn**) |
| 1 | creature type; value 4 -> class 5, value 5 -> class 6 |
| 0x3f, 0x43, 0x47, 0x1e..0x22 | read, used later (not analysed) [L] |

So N >= 0x48 (72); use **N = 80** like AddPlayer. Valid [0x33] = 1..4 (likely troop classes; real meaning unknown). Unknown slots: send 0; whether zeros crash later is unknown.
