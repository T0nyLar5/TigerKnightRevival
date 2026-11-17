# Research: input / movement and battle end (after the hero spawns), 2026-11-05 (table of contents)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Method: static analysis only. Win32 SyncClient.dll (`10xxxxxx`), Sync.dll (`10xxxxxx`) and Kingdom exe (`00xxxxxx`), private Ghidra project `ghidra_projects_c`. About 13 decompile invocations (about 30 functions), 7 minutes. Confidence tags: H = read from code, M = inferred, L = guess.
Helper analysis scripts (RTTI type-to-name mapper) were kept in the temp dir; not part of the repo.

## 0. Summary (read this first)
1. **The player's own movement is NOT lockstep input.** UE3 moves the pawn locally (client-authoritative). SyncClient only *reports* the position to the server. So after the hero exists, the server does not have to echo anything for the player to walk around. [H for the Move report, M for "nothing else is required"]
2. Client -> server messages are the `MsgReq*` family (types 0x2717..0x27c3). The lockstep frame (0x2715 MsgFramework) payload carries *Sync.dll slave messages* (ids 1..0x1a0). These are two different families. SyncClient `MsgReq*` is NOT put into the frame by the client; the real (unseen) server game logic turned Reqs into Cmds/slave messages. [H]
3. **Slave message 8 = BattleStart really does reach the UE3 side** (corrects the "unproven" in battle_launch step 5): see section 3. **Slave message 9 = BattleEnd.**
4. Blocker for "can play" is therefore most likely not input relaying but (a) the PlayerCtl/ReBorn spawn (step 5 variants 5/6), (b) BattleStart (slave msg 8) while GameEngine exists, (c) the countdown/UserLoadingFinish name match. Input-side needs are only the small list in section 2.

## Parts
- [research_input_client_messages.md](research_input_client_messages.md): section 1, client-to-server MsgReq table and the caveat on names.
- [research_input_relay_and_battle_start.md](research_input_relay_and_battle_start.md): section 2 (relay rules for battle_server.py), section 3 (slave msg 8/9, battle start and end).
- [research_input_battle_end_unknowns.md](research_input_battle_end_unknowns.md): section 4 (how the battle ends, what the lobby gets), section 5 (unknowns), test hints.
