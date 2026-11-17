# Battle spawn / troops / gear (owner test 02:34, mode 2 map 3, V44)
> rev 1 | 2026-11-08 04:50 | log analysis + V47/V48 built (offline only)

Owner observations: (1) no troops in mode 2, (2) hero spawns near top-right instead of bottom-left, (3) tutorial equipment, (4) voice absent.

## A. Spawn (verified from log battleserver_20261108_023442)
- V37-base slave AddPlayer pos was (0,0,0): `spawn_pos()` was only used for V30-36. Only DataSet slots [9],[10] (and ReBorn) carried the Camp1Pos (-404.78,-121.19) (correct = mapindex map 3 Camp1Pos).
- Client-reported hero position (0x2737): first = (325.5, 32.3, 326.2), identical in the mode-5 run (020005) -> independent of game class. Map 17 runs: (1.0, 4.2, 0.0) for the same (0,0,0) slave pos. So on map 3 the sync (0,0,0) is NOT UE origin-identity, or the client picks its own start (PlayerStart); DataSet [9],[10] are not what places the hero.
- The 0x4e23 troops + AddPerson were placed near (-402,-119), the hero is ~700 m away: the troops may have existed but out of sight (**hypothesis**, would explain "no troops").
- V47: slave AddPlayer pos = spawn_pos() (Camp1Pos). Test shows the mapping: look at the first 0x2737 in the log. Override: env TK_SPAWN="x,y,z".

## B. Troops (mode 2)
- Verified: V44 0x4e23 x3 and slave AddPerson x3 were sent (02:36:14.95/15.3) in mode 2; client reaction none (no new Req types). Nothing new to change in message content; the distance issue (above) is the only grounded suspect. V47 keeps troops at +12 s relative to the spawn (2-6 m from the hero if the spawn is honored).
- Still plausible: lobby soldier list empty (`soldier:` in client log), armyid 812001 from gameStartup.

## C. Equipment / voice
- gameStartup has no suit fields (lobby agent). Lobby now writes server\data\last_prebattle.json {armyid,suit,suit_row}.
- Mapping verified from tables: suit pos -> bag item id -> player.json items[].type = armor.txt / meleeweapon.txt / rangedweapon.txt / bullet_clip.txt id. DataSet 0x18 helmet(pos1) 0x19 shawl(4) 0x1a armor(2) 0x1b shoes(3), 0x1e..0x21 weapon1..4 (pos 6..9) [M, slot order from dataset_slots.md].
- V47 reads suit_row (fallback player.json suits[TK_SUIT|0]) and fills those slots in both AddPlayer and ReBorn (log `V47 GEAR from player.json suit`). Horse/saddle left out.
- V48 adds (**guess**): 56 face bytes (faces56) in the AddPlayer trailing string (SyncClient log string says faceLen) and 0x4c = banner item type. Voice: no known DataSet slot / battle field; voice id 101 is lobby-side only. Not done.

## Tests
Offline fake client V47/V48 (TK_MAPID=3, 17 s): gear log OK, slave pos -404.75/46.59/-121.19, troops queued, no tracebacks.
