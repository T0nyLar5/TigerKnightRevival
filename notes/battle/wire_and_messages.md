# Battle: wire format and message table (split from battle_state.md, 2026-11-08)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Message id list for all 480 ids: `re/protocol_catalog.md` (generated). Full per-message notes: `battle/msg_dictionary.md`. Frame and sync flow: `battle/sync_protocol.md`.

## 2. Wire basics
- Stream cipher: ks[n] = A[n%256] ^ B[(n//256)%256]; n from 0 per connection/direction.
  - A: x=0x1f; for i: A[i]=x; x=((((x<<5)&0xff)+0xfd)*x+7)&0xff
  - B: c=0x3f; for i: B[i]=c; t=((c*0x7a)-0x31)*c&0xff; c=(t-0x1b)&0xff
- Frame: `u16 len` (counts itself), `u16 type`, body; little endian.
- Fields: uvar = LEB128; svar = zigzag LEB128; f16 = IEEE half; str = u16 len + bytes; vec = uvar count + items; bool = 1 byte.
- MsgFramework 0x2715 (S>C): varint f1 (unused), varint frameNo (from 1), u8 flag (2 = fragment), str payload = concatenated inner `u16 len|u16 type|body` slave messages. Flushed every 50 ms even when empty.

## 3. Message table
C = confirmed, H = layout from code, M = meaning inferred, G = guess. Full table: notes\battle\msg_dictionary.md.

| id | name | dir | body | status |
|---|---|---|---|---|
| 0x3e9 | MsgConnect | C>S | u32 1, u32 a (id), u32 1, u32 c (token) | C |
| 0x3ea | MsgConnectAck | S>C | varint code (0) | C |
| 0x3eb | MsgPing | S>C | varint a, varint b; client answers 0x3eb | H |
| 0x3ec | MsgMD5Check | ? | varint, str, str | CONFLICT: listed S>C; client sends one after spawn |
| 0x3f4 / 0x279c | ClientSystemInfo / ReqSelfPing | C>S | 0 + str " [Win64]" / 2 varints every 5 s | C |
| 0x2715 | MsgFramework | S>C | section 2 | C |
| 0x2721 | ReqMove (velocity-like) | C>S | uvar uid, f16 x,y,z (y always 0); sent while moving | H; do NOT echo as position |
| 0x2737 | ReqPosition | C>S | uvar uid, f32 x3 (position while moving) | H |
| 0x2738 | ReqMoveMode | C>S | uid, mode (1/2), f16 x3 velocity m/s (jump = (0,6,0)) | H |
| 0x2754 | ? | C>S | every ~100 ms after spawn | body unknown |
| 0x2770 | ReqTroopMove | C>S | | M (echo as Cmd 0x4ece) |
| 0x274d | ReqReBorn | C>S | | M (answer 0x4e80) |
| 0x2792 / 0x2796 | ReqSelectBornPos / Confirm | C>S | after CmdShowBornPos 0x4f03 | M (answer 0x4f04 / 0x4f06, untested) |
| 0x4e20 | CmdSync | S>C | varint, str | H. **X: stuck loading** |
| 0x4e22 | CmdAddPlayer | S>C | uvar uid, u8 isSelf, svar ptype (0 normal, 1 pending, 2 watcher), str name, uvar x2, str sname, uvar x4, vec<u8> face, uvar N + N*u32 DataSet, str | H; creates PlayerCtl; same uid twice = "Player Has Exist" |
| 0x4e23 | CmdAddCreature | S>C | uvar uid, uvar N, N*u32 DataSet | H; DataSet[1]: 1 soldier, 2 horse, 4 boss; owner DataSet[0x32] must be a live PlayerCtl |
| 0x4e4a | CmdControlAiPlayer | S>C | uvar uid | G/M: client runs AI for that PlayerCtl |
| 0x4e80 | CmdReBorn | S>C | uvar uid, uvar N, N*u32 DataSet, str name, vec<u8> | H; needs PlayerCtl; calls UE3 spawn (00e19260 remote / 00df26b0 local). **Pawn appears here** |
| 0x4e92 | CmdLoadingComplete | S>C | varint | C (leaves loading screen) |
| 0x4e96 | CmdCountDown | S>C | varint state, varint value | H; section 5 |

Slave msgs (Sync.dll 0x10034630):

| id | name | body | effect | status |
|---|---|---|---|---|
| 1 | AddPlayer | uid uvar, kind svar, f0c uvar, f10 uvar, pos f16 x3, dir f16 x3, f16, bool | player unit; needs top-level 0x4e22 first | H layout, M meaning |
| 2 | AddCreature (horse) | as 1 | | H |
| 3 | AddPerson (soldier) | uid, kind svar, f0c (0), f10 (camp), pos x3, dir x3, a uvar, b f16, c uvar | a = agentType key (agentparam.txt); missing key = NULL crash | H |
| 4 | AddBullet | uid, kind, 6 f16 | | H |
| 7 | Init | header only | callback +4 | H |
| 8 | BattleStart | header only | UE3 OnBattleStart: GameEngine flag 0x20000 + script events | H |
| 9 | BattleEnd | header only | SyncClient::OnBattleEnd (+0x228=1); UE3 reaction unknown | H |
