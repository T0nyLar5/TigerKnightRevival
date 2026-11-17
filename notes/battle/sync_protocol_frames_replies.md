# Battle sync: frame cadence, reply sequence and open questions (section 10, second part)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [sync_protocol.md](sync_protocol.md) (table of contents).

Frame cadence: Sync.dll master accumulates dt and flushes a frame whenever the sum >= config field +0x28, default **50 ms** (0x101f8058 = 0x32); frameNo starts at 1 and the flush happens even when empty (callback gets size 0). [H]. The slave (not the network layer) runs the game logic and itself emits MsgCmd* to SyncClient::OnNotifyProcessLogicMsg (big switch 0x100ae390, types 0x4e21..0x4f47). So commands such as LoadingComplete normally travel INSIDE frame payloads; whether the client also accepts them as top-level messages (b41c0 default -> slave vtable+0x5c) is unknown. Therefore `battle_server.py` sends the start sequence both ways (flags `--no-toplevel` / `--no-inframe` select one).

**Req -> Cmd mapping** (client input echoed into frames): unknown; MsgReq* are 0x2717..0x27c3, MsgCmd* 0x4e20.. . Not implemented, only logged.

**Sync.dll**: exports only `ISyncMaster::Create(ISyncMasterCallback*)`, `ISyncConfig::GetSyncCompileInfo`, `ISyncSlaveHolder::Instance`, `ITerrain::Load`, `InitSyncLog`. Message classes are not exported; the master frame builder (0x10031370 ctor, 0x10031630 tick) shows frame mechanics only. Not usable as a message reference.

**Reply sequence of battle_server.py**: MsgConnectAck(0) + MsgPing -> MsgFramework every 50 ms (empty) -> after 0x3f4 (or 1.5 s): UserLoadingFinish([name]) + LoadingComplete(0) + CountDown(1,3) (2,3) (3,0) top-level and one per frame inside frames -> empty frames forever, ping at frame 100.

**What is NOT known / what the next real run tells us**: (1) does the loading screen end (then LoadingComplete is right); (2) if the client logs/crashes on a malformed message the log `server/logs/battleserver_*.log` shows exactly what was sent just before; (3) whether it sends a different message after our ack (e.g. a Req* "loaded" message, types 0x2717+) - these are decoded generically (hex) and show what the master is expected to answer; (4) the need for MsgCmdSync/scene info (0x4e20/0x4e21) if the map loads but nothing spawns.
Self-test: `tools\.venv\Scripts\python.exe -I tools\selftest_battle.py` (spare port 7791, uses the real captured encrypted bytes).
