# Face looks "all extreme" in lobby/battle
> rev 1 | 2026-11-08 02:35 | cause: faces array truncated to 14 (client reads 56)
Owner observation: every face parameter looks pushed to an extreme.
## Cause (verified statically in PoClientDLL.dll, not yet seen in game)
- Client newUser sends faces = 56 comma-separated ints (sliders ~50 default, last ~10 are small option indices).
- DLL parsers for `faces` (auth account 0x1003466f region, getSelfInfo 0x10038944 region, 0x10037ed7 region) all loop `cmp edi,0x38` = 56 entries. Notes said "14 entries" (misread hex 0x14/0x38 confusion). We sent only 14, remaining 42 became 0 = minimum slider value = extreme.
- Saved faces56 matched the client's raw data (values and order OK); only the send path truncated.
## Fix
server/handlers.py: auth account and getSelfInfo now send `_faces_list(p, 56)`; default list is 56 zeros. selftest_lobby check changed to 56 and ALL PASSED. No data migration needed (player.json unchanged; backup player.json.bak_20261108_0233_appearance).
## Open
Battle: not checked whether the battle server carries appearance (AddPlayer); none implemented. The 0x1001cc.. and 0x100377.. faces refs were not individually traced (the other two loops also 0x38).
Normal login should suffice; no need to recreate the character.
