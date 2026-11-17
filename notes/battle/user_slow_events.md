# Things that change move speed (from the user's memory of the live game, 2026-11-07)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Status: user recollection, unverified. Use as search leads for slow/speed flags.
- Drawing a bow, reloading a crossbow, using consumables (potions), raising a shield
- Using any weapon (attacks), mounting/dismounting a horse
- Interacting with world objects (opening/closing doors, repairing)
- Downed/dying state, reviving others, being hit (unsure)
- Character gender, equipment weight, executing an enemy
Leads: KingdomPawn bSlowMove_DTS / bTurnSlow (+0x580 bitfield; ue_inspect opt 5 printed raw dword 0x8C23, bit NOT decoded -> check masked value), KingdomSyncPawn bSlowDown/bInSmogSlowDownState (0), equip factors (ShoulderEquipFactor 5, UpBodyEquipFactor 9, DownBodyEquipFactor 5 = weight?).

## Brainstorm answers from the user (2026-11-07, memories 8+ years old, tested with mod A applied)
- Original start: PVE = move only after intro cutscene returns camera to hero. PVP = pick class/gear in lobby, then pick respawn point, wait countdown. Challenge/tutorial levels: maybe choose difficulty then wait for start (unsure).
- Hero spawns mounted only if a horse is equipped.
- Current battle screen: spear-plant (X) icon translucent/unusable; item slots translucent (no items?); HP bar normal; no minimap; timer 00:00; Steam overlay (FPS) can't be closed.
- Hero rotates with camera, animations OK. Double-tap W = sprint: also does nothing now. Attacks don't move the hero. Slow creep only while holding W.
