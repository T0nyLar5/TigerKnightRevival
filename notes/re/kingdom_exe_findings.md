# Kingdom exe and UE3 config findings (RE)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary: reverse-engineering notes on Kingdom-Win32-Shipping.exe, SyncClient.dll and the cracked UE3 config .bin (about 45 decompiles, 2026-11-05).
Tags: see the legend in [battle/README.md](../battle/README.md).
Source: notes/battle_launch.md section 5 and 'Battle step 5' (text moved unchanged, split 2026-11-06).

## 5. UE3 config .bin cracked [C]
`tools/uecfg.py dec|enc`. Layout: u32 version(1) | SHA1(plaintext) | payload XOR keystream. Keystream: n=len(payload); k=(n*0x3b98d+0x3aa29) mod 2^32; per byte q=(k*0x561e46a5)>>40; r=k-q*761; out^=KEY[r]; k=r+1. KEY = 761 bytes at VA 0x15d6aa0 of Kingdom-Win32-Shipping.exe (`tools/uecfg_key.bin`). SHA1 verified on all 22 files. Output: `notes/decrypted/ue_config/` (KingdomGame\config + Engine\Config). Nothing there configures hosting; `[URL] EXEName=KingdomGame.exe`, `GameEngine=KingdomGame.KingdomGameEngine`.


## Battle step 5 (Kingdom exe findings, 2026-11-05; Kingdom-Win32-Shipping.exe + SyncClient.dll, ~45 decompiles)
**Main result: the UE3 hero is NOT created by the Sync.dll slave AddPlayer (msg 1). It needs two top-level SyncClient messages we never sent: `MsgCmdAddPlayer` (0x4e22) and `MsgCmdReBorn` (0x4e80).** Variants 0-4 therefore most likely fail the same way (null IPlayerEvent, nothing for UE3).

Evidence (addresses: SyncClient.dll Win32 `10xxxxxx`, Kingdom exe `00xxxxxx`):
- SyncClient `FUN_100b41c0` (top-level dispatcher): 0x4e22 -> virtual +0x1bc = `0x100afab0` (log "Message CmdAddPlayer[Error]! Player Has Exist! Id:%u"); 0x4e80 -> `0x100b00b0` ("OnProcess_MsgCmdReBorn [%u]"); 0x4e20 -> CmdSync. Registry 0x10093050 confirms ids 0x4e22/0x4e80.
- `0x100afab0` (AddPlayer): looks up a `syncclient::PlayerCtl` by uid = DataSet[0]; if it exists -> error and nothing happens; otherwise `0x100b15d0` fills the player table, and `0x100ec400` allocates a PlayerCtl (0x1b0 bytes) and registers it (this is the IPlayerEvent that Sync.dll `0x10038440` looks up by uid; without it the unit event is null). Body byte +8 = isSelf (taken from the message, not compared with playerId in the live class; the uid==+0x20898 compare exists only in the replay class `SyncClient_PlayerVideo`).
- `0x100b4ec0`/`0x100b00b0` (ReBorn): requires the PlayerCtl (RTTI cast) and then calls the UE3 callback (`FKingdomSyncCB` vtable +4 = Kingdom `0x00ebfa30`, which calls `0x00e19260` (remote) or `0x00df26b0` (local) -> `OnSyncSpawnRemotePlayer` script event `0x00e0da60`) with position data from the PlayerCtl. **The pawn is spawned here.**
- Wire layouts (uvar=LEB128, svar=zigzag, str=u16 len+bytes; readers `0x10092e20` uvar, `0x10090d50` svar, `0x10089a00` str, `0x10020030` raw bytes) [H]:
  - 0x4e22 body = `uvar | u8 isSelf | svar ptype(0 normal, 1 pending list, 2 watcher) | str name | uvar | uvar | str | uvar x4 | vec<u8>(uvar n + bytes) | uvar N + N*4 raw bytes (DataSet) | str` (deserializer `0x10061820`).
  - 0x4e80 body = `uvar uid | uvar N + N*4 raw (DataSet) | str name | vec<u8>` (`0x10070290`).
  - DataSet indices read: [0]=uid, [2]=alive (0 + ptype 0 + not self = "Remote Player Has Dead" branch), [0x10]=camp, [0x3e] (config lookup 0x10046950), [0x44], [0x49], [0x4a]: so **N must be >= 75**; we send 80 zeros except [0]=uid,[2]=1,[0x10]=1. Real meaning of the other slots (hero id, equipment) is unknown (needs config tables).
- Local uid match: `isSelf` byte in the AddPlayer message + PlayerCtl keyed by DataSet[0]; ReBorn compares msg uid with `this+0x68` (set when the self PlayerCtl is processed). playerId 10001 from MsgConnect is only used by us as DataSet[0].

Verdicts for the earlier assumptions:
- Variant 0 (slave AddPlayer + BattleStart only): CONTRADICTED as sufficient (no PlayerCtl, no ReBorn); slave layout itself CONFIRMED (Sync.dll `0x10033c60`, `0x10038440`).
- `kind` field of slave msg 1: UNKNOWN (only stored; not verified against config tables; 0 is probably accepted but unverified).
- Variant 1 (Init(7)): UNKNOWN; msg 7 only calls slave-callback +4 (no UE3 sign of need).
- Variant 2/3/4 (CmdSync): CmdSync only sets a flag in SyncClient (0x100b41c0: `[+0x98]=1`) -> UNKNOWN/harmless; troops via AddPerson in frames: UNKNOWN.
- msg 8 BattleStart starts the countdown: UNKNOWN/probably NOT. Slave msg 8 runs a callback on the slave-callback object (Sync.dll `0x10036f60`). On the UE3 side `FKingdomSyncCB` has a BattleStart handler (`0x00e9edc0`, vtable +0xa4: sets game flag 0x20000, fires script events "BattleStart"), but I could not prove msg 8 triggers it.
- Countdown: top-level 0x4e96 CountDown(state,value) calls `FKingdomSyncCB` vtable +0xb0 = `0x00ebfb00`, which stores state/value at +0x154/+0x158 and, for state 1, fires two script events (names at 0x0170bb90/0x0170bb88) plus UI `0x00e6e1e0` - it needs `GameEngine` (0x01717054), a local player controller and a spawned hero (`0x00d3d1a0`, `0x00ea32c0`); it returns early when those are missing. So our countdown messages had no effect because no hero existed: CONFIRMED as the likely cause of the frozen timer.
- `LoadingComplete` (0x4e92) -> cb +0xcc = `0x00eb2690`: sets flag (+0x14c), updates team counts from the player list - consistent with leaving the loading screen: CONFIRMED (map did load in the test).
- `UserLoadingFinish` -> `0x00ea7f60` ("FKingdomSyncCB::OnUserLoadingFinish:") marks players of the player list whose name matches (wide compare) as loaded; the name must match a player list entry (from the lobby/MsgLoadPlayerCache?) - UNKNOWN whether our name matches.

New variants (code unchanged for 0-4; selftest passes for 0-6; launcher menu has 5, 6):
- **5** = CmdSync, top-level MsgCmdAddPlayer(0x4e22, isSelf, uid 10001) before the first frame; frames: Init, slave AddPlayer, BattleStart; top-level MsgCmdReBorn(0x4e80) then the loading/countdown sequence. Best bet.
- **6** = like 5 but without slave AddPlayer (in case PlayerCtl creation registers the slave unit itself) and ReBorn 1 s after the loading sequence.
Req after spawn (goal 2): still UNKNOWN from the exe. SyncClient has handlers for MsgCmdShowBornPos / SelectBornPos (`0x100b60d0` -> cb +0x294) and the exe exposes `SyncConfirmBornPos`/`IsBattleStarted` natives (strings 0x10b708c, 0x10bb440); if the map needs a born-point choice the client will send MsgReqSelectBornPos(+Confirm), visible as `RECV [after spawn]` in the log. Recommended test order tonight: **5, then 6, then 3, then 0**. Reply to a Req: for SelectBornPos send MsgCmdSelectBornPosConfirm (type unknown, find via registry 0x10093050 + sp_counted names) - not implemented.


