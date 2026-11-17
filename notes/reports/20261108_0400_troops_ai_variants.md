# Troops + enemy AI variants V44/V45/V46
> rev 1 | 2026-11-08 04:00 | new variants built on V37; offline-checked only, UNTESTED in game

Base: V37 (hero walks; V43 tutorial echo dropped, not needed off map 17). Map: use **3 (博望坡)**: loaded in V25/26; spawn from mapindex Camp1Pos (-404.78, 46.09, -121.19) already in `SPAWN_BY_MAP`; boss/camp-2 point (102.63,43.19,341.11) is ~480 m away, so the enemy is placed 15 m from the hero instead. Not map 17 (no camp positions, tutorial scripts), not map 11 (spawns under map). Walk helper writes the hero Location into a global (exe+0x195F340), so it should work on any map [hypothesis; not verified on map 3 with V37].

Timeline (ms after client info, V37 recountdown at +8 s untouched):
- V44: +12 s three top-level 0x4e23 (uids 20001-3, owner = hero 10001, camp 1, class 1, soldier-id slots 0x3f/0x43/0x47 = 112011, DataSet pos slots [9],[10] set), +0.3 s slave msg 3 AddPerson (kind 1, a 1) at spawn +2/+4/+6 m x, +2 m z. Same recipe as V8/V29 (never seen in a walking battle). Confidence troops appear: 35%.
- V45: V44 + at +16 s enemy hero uid 30001, camp 0: top-level 0x4e22 (isSelf 0), +0.3 s slave AddPlayer (kind 1, f10 0), +0.8 s 0x4e80 ReBorn, +1.5 s 0x4e4a ControlAiPlayer. Position spawn +15 m x. Confidence appears 40%, moves/attacks by itself 20% (AI mode 0x13/0x2f gate unknown, research_ai.md).
- V46: V45 + at +20 s enemy troops 30101-3 (owner 30001, camp 0) beside the enemy. No MatchEnd (V29's +150 s end dropped to keep tests isolated).
Never sends CmdSync.

Watch in game: soldiers standing near hero (friendly, not attacked); enemy hero 15 m ahead; does it walk/attack; crash or loading hang at +12/+16/+20 s; duplicate hero.
Log lines: `V44 TROOPS: uids=...`, `SEND V44 add_creature(...)`, `V44 TROOPS: slave AddPerson queued`, `V45 ENEMY`, `SEND v45 control_ai_player`, `V46 TROOPS`. Success also = new `RECV [after spawn]` Req types carrying uid 30001 or 2000x (AI output; would need a relay).
Offline: fake client run of 44/45/46 (25 s each): 3/3/6 0x4e23 and slave msg 3, 0x4e22 x2, one 0x4e80/0x4e4a for 45/46; existing `tools\selftest_battle.py` all PASS; no listeners left.
Test order: 44, then 45, then 46. If 44 breaks the walk, troops DataSet/AddPerson is the culprit.
