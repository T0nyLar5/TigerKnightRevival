# Battle sync: server to client message table (section 10, first part)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [sync_protocol.md](sync_protocol.md) (table of contents).

## 10. Server->client protocol (SyncClient.dll, Win32 build, 2026-11-04) and `server/battle_server.py`
Method: static analysis of the message registry (init fn 0x10093050 registers `(type, serializer, deserializer)` via 0x10092c10; class names read from RTTI of the shared_ptr control blocks), the receive loop (0x100ade96..0x100ae240), dispatchers 0x100ade00/0x100ae390/0x100b41c0, and Sync.dll's master frame builder (ISyncMaster::Create -> 0x10031370). Confidence: H = read directly from code, M = layout read but meaning inferred, L = guess.

**Encoding**: header `u16 len | u16 type`; body field kinds: fixed u32 (only MsgConnect), LEB128 varint (everything else, e.g. -1 = `ff ff ff ff 0f`), string = u16 len + bytes, vector = varint count + items. Two separate cipher objects (init 0x100da1c0 called twice), so each direction has its own counter from 0. [H/M]

**Client -> server (seen in capture)**: 0x3e9 MsgConnect (4 x u32) [H]; 0x3f4 MsgClientSystemInfo = varint 0 + string " [Win64]" [H] (`00 | 08 00 | 20 5b 57 69 6e 36 34 5d`); 0x279c MsgReqSelfPing = 2 varints (`e7f4a1fb06` looks like a timestamp/token, then -1) every 5 s [H layout, M meaning: latency probe]. No reply was ever needed to keep the connection alive (client idled 70 s without dropping).

**Server -> client**
| type | name | body | what the client does | conf |
|---|---|---|---|---|
| 0x3ea | MsgConnectAck | varint code | queue loop calls UE3 callback vtable+0x264 ("connected") then 0x100b6910 | layout H, effect M |
| 0x3eb | MsgPing | varint a, varint b | client answers with 0x3eb {its time, b} (handler 0x100b0e70) | H |
| 0x3ec | MsgMD5Check | varint, string, string | non-empty first string -> error event 6, else 7 | M, not sent |
| 0x3ee | MsgPingVal | varint playerId, varint ping | stores ping of player | M, not sent |
| 0x2715 | **MsgFramework = lockstep frame** | varint f1, varint frameNo, u8 flag, string payload | 0x100af840: flag 2 = fragment, appended to a map keyed by frameNo; any other flag = complete, delivered with (frameNo, payload) to the slave simulation (Sync.dll ISyncSlave, vtable+8). payload = concatenated inner messages `len|type|body` | layout H, f1 meaning L (unused by client), flag value for "complete" M (0 used) |
| 0x4e20 | MsgCmdSync | varint, vector | top-level, goes to slave vtable+0x50 and sets a "synced" flag ([this+0x98]=1); probably the world snapshot | M, NOT sent (content unknown) |
| 0x4e91 | MsgCmdUserLoadingFinish | varint, vector<string> names | logs "Loading Finish User List", calls UE3 cb vtable+0xc8 per name | H |
| 0x4e92 | MsgCmdLoadingComplete | varint | logs "Loading Complete !", calls UE3 cb vtable+0xcc. **Best candidate for "leave loading screen".** | H effect, M that it ends the loading screen |
| 0x4e96 | MsgCmdCountDownUpdate | varint, varint state, varint value | calls UE3 cb vtable+0xb0(state, value); state 3 also bumps a counter and starts something (0x1003eda0) | layout H, state meaning L (guess 1,2 = countdown, 3 = running) |
