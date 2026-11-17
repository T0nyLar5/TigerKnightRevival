# Sync position feed: V41/V42 (2026-11-08 00:00)
## 1. V38/V39 logs (VERIFIED)
- battleserver_20261107_221923.log = V38, ..._222053.log = V39. Echo was sent correctly (e.g. 0x2737 (0.97,4.17,-0.15) -> Cmd 0x4eca `91 4e bb 3b 2b 44 aa b0` = uid 10001 + f16 0.967, 4.168, -0.166; encoding and uid right).
- Client reaction: NONE. Same message mix as V37 (about 375x 0x2737, 370x 0x2721, no new types) and still 5-6 pull-backs of 9-10 m to the start (max radius 10.9-11.0 m). So the top-level Cmd 0x4eca either does not feed the pawn's leash target or is not the right path. Conclusion: top-level GhostPosition is for OTHER players' ghosts (IPlayerGhostCtl), not the local hero.
## 2. Static finding (Sync.dll Win32 + Win64 dispatcher 0x180036eb0, same switch)
- Sync.dll has slave messages named MsgMove, MsgMoveActionStart, MsgMoveActionEnd, MsgPosition, MsgSetPositionEnabled (RTTI) = the in-frame counterparts of the client Reqs. They go through SyncSlave dispatcher (Win32 0x100348c0) INSIDE 0x2715 frames, per unit uid.
- Registry 0x100450e0 layouts (deserializer creators): 401 (0x191) = uvar uid, f32 x3 (reader 0x1003e180 = 4 raw bytes) = EXACTLY the 0x2737 ReqPosition body. 402 (0x192) = uid, uvar, f16 x3 = EXACTLY 0x2738 MoveActionStart body. 403 (0x193) = uid, uvar = 0x2739 MoveActionEnd body.
- Handler 401: Walker cast, FUN_1005ace0(vec3) (Win64 FUN_18005e7f0): if unit state (+0x54 in {0,2}, +0x30 != 0) and current act not in a blocking set (6,0xf,0x10,0x13,0x15-0x18) creates a walker act that moves the SYNC unit to that position. This is the missing "sync-side position" writer; the unit's position change calls the UE3 listener (unit+0x114) which very likely ends in the pawn setter FUN_00db5ef0 (hypothesis; db5ef0 has only vtable refs, caller not traced).
- Other ids with uid+vec: 200 (seek, uid + 5 f16 + bool...), 226 (0xe2 two vec3), 102 (uid,target uid, 6 f16, 2 bool; DEPEND family 100-105 = riding/attach, not moves).
- Not done: Win64 registry layouts not re-read (Win64 dispatcher case numbers identical); caller of FUN_00db5ef0 not traced (vtable slot unknown).
## 3. Variants
- V41 = V37 + for each client 0x2737 append `frame(401, body verbatim)` to the next 0x2715 payload (pending queue, one entry per 50 ms frame). Nothing top-level. Log: "v41 IN-FRAME slave 401 <- client 0x2737" every 20th.
- V42 = V41 + 0x2738 -> slave 402, 0x2739 -> slave 403 (same bodies).
- Risk: if the hero unit is not a WalkerSlave the cast returns NULL and the game may crash (PlayerSlave is cast to Walker without null checks elsewhere, so unlikely). Queue lag: 20 msgs/s vs 20 frames/s (small).
## 4. Test order
V41 (walk >12 m away; success = no teleport back; jump still works), then V42. If V41 crashes/ignores: report the log (look for "can not find uid" or lag). Confidence V41 right path: about 55%.
