# Battle: walking, speed factor and snap-back (split from battle_state.md, 2026-11-08)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary and current status: `battle_state.md`. Ruled-out list with report pointers: `battle/walk_gate_*.md`, `reports/20261107_0230_battle_state_archive_8b_10.md`.

## 7. Walking, speed and snap-back
- Walking gate solved by V37. The client's speed comes from controller fPersonToSelf/HorseMaxSpeedFactor = max(slot,1e-4) (Win64 0x140aee73f / 0x140aee765), read from DataSet 0x26/0x27. Dead ends (script gates, challenge flags, root motion, collision, memory-written speed factors, server Cmd echoes): see the archive report and notes\battle\walk_gate_*.md.
- Snap-back (hypothesis ~60%, Win64 Ghidra + CE trace): sync object DAT_14195f340 (+0x14 base pos, +0x20 working), pawn DAT_14195f338. Callback FUN_140ae0370 (MultiPointCheck x5 + FarMoveActor pawn -> obj+0x20) is the teleport. Setter FUN_140aaf020 (vtable-only) writes obj+0x14; nothing calls it, so +0x14 stays at spawn. The leash check and the setter caller are not traced.
- FUN_140aaf020 = native UScript `KingdomPawn.ForceUpdatePlayerHumanLocation(Vector)` (exec thunk 0x140a51a50, vtable+0xaf8). No server-side entry.
- Failed (client did not react): echoing each 0x2737 position as Cmd 0x4eca (V38/V39), and in-frame slave 401/402/403 (V41/V42).
- Key J of `英雄速度檢查.bat` reads the sync object.
- Reports: 20261107_2200_pullback_echo, 20261108_0000_sync_position_feed, 20261108_0100_v41_log_check, 20261108_0200_snapback_writers, 20261108_0300_walk_helper.
