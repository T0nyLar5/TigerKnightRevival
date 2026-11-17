# Battle server to client protocol (SyncClient / Sync.dll) (table of contents)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary: SyncClient step 1 results, the server->client frame protocol with battle_server.py message layouts, and the step 3 spawn/battle-start notes.
Tags: see the legend in [README.md](README.md).
Source: notes/battle_launch.md sections 8, 10 and 'Battle step 3' (text moved unchanged, split 2026-11-06).

## Parts
- [sync_protocol_step1_wire.md](sync_protocol_step1_wire.md): section 8, step 1 results (direct launch command line, SyncClient wire format, MsgConnect).
- [sync_protocol_messages.md](sync_protocol_messages.md): section 10, encoding and the client->server and server->client message tables.
- [sync_protocol_frames_replies.md](sync_protocol_frames_replies.md): section 10, frame cadence, Req->Cmd mapping, Sync.dll exports, battle_server reply sequence, open questions, self-test.
- [sync_protocol_step3_spawn.md](sync_protocol_step3_spawn.md): "Battle step 3", spawn and battle start (slave message ids, AddPlayer, BattleStart).
