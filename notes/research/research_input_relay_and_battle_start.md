# Research: input and movement, part 2 (sections 2-3: relay rules, battle start and end in the slave)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_input.md](research_input.md) (table of contents).

## 2. Concrete relay rule for battle_server.py
Because this is solo play, the minimal rule set is:
- **C>S 0x2721 MsgReqMove, 0x2737 MsgReqPosition, 0x2738/0x2739 MoveActionStart/End, all attacks, 0x279c ping**: log and do NOT echo. The local pawn already moves; echoing a Cmd for our own uid could be applied to our own pawn or hit the "Player Has Exist" style errors. If later a visible remote avatar is wanted, the only safe echo candidate is `Req type 0x2738 -> top-level Cmd 0x4e50` and `0x2739 -> 0x4e51` with the *identical body* (shared codec). Untested.
- **C>S 0x2792 / 0x2796 (SelectBornPos / Confirm)**: answer with `CmdSelectBornPos` 0x4f04 / `CmdSelectBornPosConfirm` 0x4f06 using the identical body (shared-name pairing, M).
- **C>S 0x274d (ReBorn)**: answer with top-level `MsgCmdReBorn` 0x4e80 for the same uid (already implemented in variants 5/6).
- Unknown Req types: keep logging hex under `RECV [after spawn]`; that is the real test for which Reqs appear.
Frame-slot layout: there is no per-player input slot. A frame is `varint f1 | varint frameNo | u8 flag | string payload`, payload = `u16 len | u16 id | body` slave messages; a unit-targeted slave message has `uvar uid` as the first body field (SyncSlave dispatcher `0x100348c0`: unknown uid -> log "can not find uid"). Slave messages for movement exist (Sync.dll classes `UMsgMove`, `UMsgPosition`, `UMsgMoveActionStart`...; ids not resolved) but are server-to-all output, not what the client sends. [H on layout, ids of unit messages unknown]

## 3. Battle start / end in the slave (Sync.dll `0x10034630`, switch is on `id-1`)
Corrects an earlier reading. Callback object = SyncClient slave-callback vtable `0x102214dc` (slots: +4 `0x10003a80` empty?, +8 `0x100af610`, +0xc `0x100af720` unit event, +0x10 `0x100b0b40`, +0x14 `0x100af550`, +0x18 `0x100af5e0`).
| slave msg id | action | conf |
|---|---|---|
| 7 | callback +4 (empty-looking function `0x10003a80`), header only | H |
| **8** | `FUN_10036f60`: sets slave running flag +0x2c=1, then callback +0x14 = **SyncClient `0x100af550` "OnBattleStart"**: sets `this+0x6c=1` ("battle started") and calls UE3 cb vtable +0xa4 = Kingdom `FUN_00e9edc0`, which does `GameEngine[0x392] |= 0x20000` and fires the script events (names 0x0170bb90/88, 0x0170b5c8). So **msg 8 does start the battle on the UE3 side** (needs `GameEngine` DAT_01717054 non-null, true after map load). A gate in 0x100af550: if state (+0x508)==12 and (+0x2b4)->0xc==0x10 and +0x5bc==0 it skips the extra init call. | H |
| **9** | clears running flag, callback +0x18 = **`SyncClient::OnBattleEnd` (0x100af5e0)**: logs "SyncClient::OnBattleEnd", sets `this+0x228=1`, calls `FUN_1000cba0`. Header only. | H |
| 0xa | callback +0x20 with 1 byte | H |
| 0xc | clear running + callback +0x28 | H |
| 0xd | callback +0x2c(0) | H |
| 0xe | clear running, callback +0x64 on `+0x190` and +0x34 | H |
| 0xf | callback +0x38 (1 byte) | H |
| 0x10 | callback +0x54 (uvar at +8) | H |
Top-level end-of-match Cmds that exist in the registry: `MsgCmdMatchEnd` (0x4e73, shared codec 0x100515b0 = single varint), `MsgCmdInnerMatchEnd` (0x4f0a?), `MsgCmdBattleRoyaleEnd` (0x4f2d), `MsgCmdChallengeMatchResult` (0x4ebc). Names reliable only for 0x4e73 (own codec/class); M.
