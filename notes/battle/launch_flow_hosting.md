# Battle launch: protocol, hosting verdict and open leads (sections 3-4, 6-7)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [launch_flow.md](launch_flow.md) (table of contents).

## 3. Battle protocol / validation / results
- UE3 `AKingdomSyncGame::InitSyncClient` (Shipping exe 0xec3360) reads options ip (default 127.0.0.1), port, id, map, VideoFileAddress, then calls delay-loaded `SyncClient.dll!ISyncClient::Create(ip, port, uint id, 1, uint X, cb, int, eBattleMode, lang, bool)` [C]; X is probably the Token property [G]. SyncClient has TcpConnector and KcpConnector (boost.asio), messages MsgConnect/MsgConnectAck/MsgPing/MsgBattleStart etc. Native UE3 networking is not used for Sync modes.
- Validation = battle server checks (playerId, token) that the lobby handed out [G]; we control both ends, so any uint works.
- Results: battle server -> lobby (internal, unseen) -> lobby pushes `gameResultGlance` and `gameResult` (C++ OnNotifyGameResult, Lua `MainMenu_Fighting_On_GameResult` id 105). The UE3 client does not report results to the lobby. The fake lobby must synthesize these pushes itself.

## 4. Can we host it? Verdict
- UE3 exe has stock UE3 `-server`, `Listen`, `ServerTravel`, `-nullrhi` code, and TcpNetDriver config, but all battle classes are *Sync* games needing a Sync master. No master exists in the client: SyncClient.dll imports only ISyncSlaveHolder/ISyncConfig from Sync.dll. [C]
- `Sync.dll` (x86 and x64 shipped) exports `ISyncMaster::Create(ISyncMasterCallback*)`, `ITerrain::Load`, i.e. the authoritative simulation (Msg* classes, AI) is present as a library, but the server transport and server executable are NOT shipped. [C]
- Verdict: pure listen/dedicated UE3 hosting: not feasible. Self-hosted battle: feasible only with a custom host program loading Sync.dll (32-bit) + reimplementing the SyncClient wire framing. Heavy (days). Confidence medium-high on "not trivial", low on effort estimate.
- Free offline path: replay playback (`OnReplayVideo` -> `?VideoFileAddress=`, `ISyncClient::CreateToPlayVideo`) needs no server, but no replay files exist locally (SavedVideo absent) [C].
- Tutorial: mode 1/4/5 are also Sync games (connect to ip:port). No fully local tutorial found. `On_ReqSetTutorial` is only a lobby ack.


## 6. Unresolved
- `.u/.upk` use tag `TK01`: header ints/strings are XORed per Serialize call with the same keystream (chunk length n selects the mask; for 4 bytes the mask is cf 74 83 49), version 865. Package flags have StoreCompressed, compression flag 2 (LZO): chunk table is plain, chunk = standard 0x9E2A83C1 block header at file offset 145 for Core.u. Name table/script bytecode NOT extracted (my LZO decoder attempt failed; not committed). So `Token` handling in UnrealScript is unverified.
- config.cfg / config_client.cfg / terrain.cfg (map index, server tables): different cipher, not cracked (loader: Sync.dll 0x100b9060, 0x100bb0c0).
- Exact `gameStartup` JSON nesting and MsgConnect layout.

## 7. Best next lead
Decode `MsgConnect`/`MsgConnectAck` and the frame format in SyncClient.dll (`TcpConnector`, entered via ISyncClient::Create at 0x100acb80, connect call is vtable+4 with (ip,port,id,1,X)). Run a stub TCP listener on the lobby-supplied port to log what the client sends (needs a user-run test). Then decide between replaying a canned stream and hosting Sync.dll's ISyncMaster.
