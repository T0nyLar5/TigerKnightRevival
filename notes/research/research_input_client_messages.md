# Research: input and movement, part 1 (section 1: client to server messages)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [research_input.md](research_input.md) (table of contents).

## 1. Client -> server input messages
Wire format (all varint-style, same as the other messages): `u16 len | u16 type | body`; uvar = LEB128; f16 = IEEE half float (2 bytes, table at SyncClient `0x10224ee8`, reader `0x10091480`, writer `FUN_10020f00`).

| type | name | body | where it is sent | conf |
|---|---|---|---|---|
| 0x2721 | MsgReqMove | `uvar uid | f16 x | f16 y | f16 z` | SyncClient `0x100160e0`: called by UE3 with the new position; sends ONLY when the position differs from the unit's stored position by more than a threshold (DAT_10275de0). uid = `unit+0x5c` (the hero's unit uid, i.e. the uid used in AddPlayer = playerId 10001 in our setup). If the unit is on a horse (IHorseCtl) the horse position is used. Serializer `0x1004ca30`, factory `0x1004d1a0` | H |
| 0x2737 | MsgReqPosition | own codec `0x1004ff90`/`0x1004ff70` (layout not read) | periodic position sync, probably | M |
| 0x2738 / 0x2739 | MsgReqMoveActionStart / End | codec `0x100500a0`/`0x10050080`; End uses a generic one-varint codec | start/stop of the walk animation state | M (id-name match) |
| 0x2717 | MsgReqAction | generic codec | attack/skill actions | L (id-name match is noisy for generic codecs) |
| 0x2723 | MsgReqShot, 0x2724 MsgReqContinueShot | own codecs | ranged attacks | M |
| 0x2792 / 0x2796 | MsgReqSelectBornPos / MsgReqSelectBornPosConfirm | | only after the server sent CmdShowBornPos (0x4f03) | M |
| 0x274d | MsgReqReBorn | | respawn request | M |
| 0x2750 | MsgReqTutorialStep | | tutorial map (mapId 17 is the tutorial/training ground!) | M |
| 0x279c | MsgReqSelfPing | | already handled (capture-confirmed) | H |

Caveat on names: the type->name table was derived from RTTI (`sp_counted_impl_p<MsgReqX>` constructor reachable from the registry codec). It is reliable only when the codec function is message-specific (Move, Position, MoveActionStart, Shot...). It is wrong by one for SelfPing (table says 0x279b, capture says 0x279c), so treat generic-codec entries as guesses. The full table is reproducible with the same method (script not kept).

### Req and Cmd are the same family
`MsgReqX` and `MsgCmdX` pairs often share the codec function, e.g. ReqMoveActionStart 0x2738 and CmdMoveActionStart 0x4e50 (`0x10050080`), ReqMove 0x2721 and CmdGhostPosition 0x4eca (`uid + 3 x f16`), ReqTroopMove 0x2770 and CmdTroopMove 0x4ece. So the original server broadcast "Req body with a new type" as Cmd to the other players. There is no MsgCmdMove; the remote player position arrives as CmdGhostPosition (0x4eca) or as a slave message (below). [M]
