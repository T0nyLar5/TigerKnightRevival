# Walk gate: native findings, V27/V28 and V29 analysis
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [walk_gate_v27_mod.md](walk_gate_v27_mod.md) (table of contents).

## Native findings (11-05, V27)
- Tools: tools\work\props.cs (UProperty list per class; build with Framework64 csc against Eliot.UELib.dll), scan.py/findptr.py/vt2.py (byte scans of the exe).
- GameReplicationInfo native layout (Kingdom Win32 exe, replication fn 0x7203c0): bits live in the dword at **GRI+0x1cc**: bStopCountDown = 0x1, **bMatchHasBegun = 0x2**. (bIgnoreMoveInput is in Engine PlayerController; not located.)
- The ONLY `or [reg+0x1cc],2` in the exe is at **0x753e50**, inside a GRI-family virtual (vtable slot 0x23c, fn 0x753e10; 9 vtables spaced 0x398 from 0x13cb3b0). Logic: super(arg); if (bStopCountDown set) and vfunc[0x394]() == 0 and object at GRI+0x1d0 is valid -> call its vfunc 0x164, then set bMatchHasBegun. So it is **NOT driven by a Sync Cmd**: bStopCountDown is set by script `KingdomSyncGame.MatchInProgress.Timer`, i.e. the local KingdomSyncGame must be in state MatchInProgress with its Timer running (StartMatch from PendingMatch.BeginState).
- Script: KingdomGame.StartMatch never writes bMatchHasBegun; `ReadyToStartMatch` returns false; NotifyMatchStarted is native (exec thunk 0x7d51f0).
- Countdown handler 0xebfb00: state 1 = freeze (flag 0x4000000 on GameEngine+0x59c); state 2 clears GameEngine[0x392] bit 0x20000, value 0 sets it back; any other state (3) clears bit 4 at +0x838 of the local controller (FUN_00db1e50) and, if previous state was 2, sets 0x20000. It does NOT touch the GRI.
- Therefore no Sync Cmd is known that sets the bit. V27 (re-run BattleStart + countdown (3,0)(2,0)(3,0) at +8 s, hero present) and V28 ((1,0)(2,0)(3,0)) are guesses to hit the +0x838 clear after the hero exists. Next idea if both fail: find the exec/vfunc 0x394 and the +0x1d0 object (what must be valid), or check via logs whether KingdomSyncGame ever reaches MatchInProgress (script Timer).

## V27/V28 result (11-05 late) and V29 analysis
- V27/V28 tested: HUD + sound appear, still no walking. Countdown msgs reach the client; 0xebfb00 never touches the GRI.
- Local game = KingdomSyncGame: PendingMatch.BeginState -> StartMatch -> state MatchInProgress; its Timer only sets bStopCountDown. KingdomGame.StartMatch does NOT call GRI.StartMatch and never writes bMatchHasBegun. Only writer is native 0x753e10 (Win32 exe; GRI-family Tick, vtable slot 0x23c): needs bit0 set, vfunc[0x394]()==0 and an object at +0x1d0 (not pending-kill, flag 0x80 at +0x6c), then `or [esi+0x1cc],2` at 0x753e50. Nothing in the Sync protocol drives these, so NO server message is known to work (no V29 server variant).
- Client patch option (untested, Win32 addresses; Win64 build needs the equivalent address): at 0x753e1d replace the 7-byte `test byte [esi+0x1cc],1` with `EB 31` (jmp to 0x753e50) so bMatchHasBegun is set on every tick. Also still need IsMoveInputIgnored()==false (controller bIgnoreMoveInput); unverified which of the two gates is actually closed.
