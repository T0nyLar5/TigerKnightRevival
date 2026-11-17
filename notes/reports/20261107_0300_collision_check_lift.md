# ue_inspect options 8 (collision check) and 9 (lift experiment), 11-07 (selftest only, not run in game)
Hypothesis (untested): hero embedded in floor / collision cylinder never initialised (InitWithPawnInfo not called) -> every horizontal MoveActor blocked, jump escapes upward.

## Option 8 --coll (read only)
Prints hero CylinderComponent and CollisionComponent (object, class, CollisionRadius, CollisionHeight; "null" = no cylinder), Pawn Floor vector, bCollideWorld/bBlockActors/bCollideActors, MaxStepHeight, WalkableFloorZ, Mesh Translation, then up to 15 Actors within 300 units (name, class, distance, location, bBlockActors).
- Bool decode: Walker.learn_bm finds the UBoolProperty.BitMask dword offset at runtime (the offset after Offset_Internal where >=95% of the hero's bool property objects hold a single set bit and values differ); value = (dword at obj+Offset) & BitMask. If not learnable prints "?" for bits (the BitMask offset is printed so it can be checked).
- Nearby actors: scan of GObjObjects, class must chain to "Actor", not *Component, not Default__; Location read via the class's Location property.
- Reading guide: radius 0 / height 0 or null cylinder = collision never initialised (expected under the hypothesis); normal values (about 34 / 88 for humans) and bBlockActors fine = look at nearby actors (is something at distance < radius with bBlockActors 1?) and Floor.
## Option 9 --lift (writes Location z once)
Asks height (default 150), Enter, 5 s countdown (user switches to game and holds W), then writes Location.z += height and Velocity = 0 once, samples Location every 0.25 s for 5 s with a remaining-seconds counter, prints x/y/z delta. Writes nothing else. Needs admin.
- Interpretation: x/y moves while airborne/falling = collision/floor embedding is the blocker; x/y still ~0 = not collision (the pin is elsewhere).
## Files
tools\ue_inspect.py (collision_check, lift_experiment, Walker.prop_obj/learn_bm/boolv, mock extended), server\text\probe_menu.txt, 英雄速度檢查.bat (keys 8, 9; ASCII+CRLF verified). `ue_inspect.py --selftest` OK.
