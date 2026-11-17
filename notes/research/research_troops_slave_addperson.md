# Research: troops, part 2 (section 3: slave AddPerson wire layout and meaning)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_troops.md](research_troops.md) (table of contents).

## 3. Slave AddPerson (msg 3) wire layout and meaning [H layout; Sync.dll]
Body = `uid uvar | kind svar | f0c uvar | f10 uvar | 6 x f16 (pos xyz, dir xyz) | a uvar | b f16 | c uvar` (reader `0x1003be20`, handler `0x10033e40`). AddCreature (msg 2) has the identical layout (`0x10033d40`).
- uid: same as DataSet[0] of the Ctl made by 0x4e23. With no Ctl the event cast fails -> default null event, no UE3 spawn. [H]
- **a (uvar after the floats)**: used by `FUN_10021430` as the key of a map loaded from **terrain.cfg** (`FUN_100204d0` -> `FUN_100b9060("terrain.cfg","terrain")`; file `Binaries\Win32\terrain.cfg`, 195 MB, encrypted, separate from config.cfg), log text "can't find agentType(%d) of config". On a miss it passes a NULL config pointer to `FUN_100658a0`, which copies 0x44 bytes from it = **NULL dereference = crash**. So `a` must be a valid agentType. Bullets use constant 3, so **3 exists**; use `a=3` for troops. The variants 3/4 in battle_server (and AddPlayer) sent 0, which may crash. [crash path H; M that the key is `a` rather than `kind`, decompiler args are shifted]
- kind svar, b (f16 -> unit+0x7c), c (uvar -> unit+0x8c / player entry +0x24c): only stored. `a` and `kind` are also passed to slave-callback vtable+0x4c, result stored in the player table +0x238.
- f0c = `DependOnAdd` depId (`0x10033f40`): uid of ANOTHER unit this one depends on (rider/mount style); unknown id only logs "DependOnAdd: can not find depId[%d]". **Not an owner link**; troops: f0c = 0.
- f10 copied to unit+0x70 and player-table +0x248 (probably camp/team): keep equal to the hero's f10.
- **The troop->hero link is only DataSet[0x32] (and 0x35) of the 0x4e23 message.**
