# Battle: DataSet slots (split from battle_state.md, 2026-11-08)
> rev 2 | 2026-11-08 04:20 | DS[0x3e] = soldier name (verified); 0x44 is a row stat counter; V52 zeroes 0x44/0x49/0x4a
Used in CmdAddPlayer / CmdAddCreature / CmdReBorn bodies. Slot 0x26/0x27 = walking fix (see battle/walk_snapback.md).

## 4. DataSet (N x u32 LE)
- Use **N = 132** (UE3 reads index 0x7e; keep 4N + ~60 < 1024).

| idx | meaning | status |
|---|---|---|
| 0 | uid | H |
| 1 | creature type: 1 soldier, 2 horse, 4 boss | H |
| 2 | HEALTH (0 = remote dead). Hero 200, soldier 130 | M |
| 5,6,7 / 9,10 | dir x,y,z / pos x,y (raw f32; pos z = 0) | M |
| 0x10 | camp / team | H |
| 0x18..0x1b | helmet, shawl, armor, shoes ids (armor.txt) | M |
| 0x1e..0x21 | weapon 1..4 ids (meleeweapon / rangedweapon.txt) | M |
| 0x26, 0x27 | hero speed factors: must be 1.0f (V37 fix) | verified |
| 0x32 | owner uid (soldiers: hero uid) | H |
| 0x33 | SoldierKind: 1 foot, 2 archer, 3 cavalry, 4 horse archer; other = no pawn | H |
| 0x35 | commander uid (= hero uid) | M |
| 0x4c, 0x56, 0x57 | local player flagID, HairStyle | M |
| 0x4d | nonzero = mounted spawn | M |

- Current values: hero uid 10001, camp 1, hp 200, gear 17000011/17100001/17200001/17300001, weapons 18051001/18052001 (armytype 112011). Soldiers: hp 130, [0x33]=1.
| 0x3e | hero soldier id -> scoreboard soldier name (verified, V51) | V |
| 0x44, 0x49, 0x4a | were 112011 (V21 guess); 0x44 feeds a row stat counter (not troops); V52 sets 0 to find the scoreboard total | H |
