# Walk gate: where movement input is zeroed
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary: the decompiled KingdomGame.u code that zeroes movement input (bIgnoreMoveInput), what sets and clears it, and the conclusion.
Source: notes/walk_gate.md sections 1-Conclusion (text moved unchanged, split 2026-11-06).


Tooling: `tools\updec.py plain <KingdomGame.u> tools\work\KingdomGame_plain.u` writes a plain UE3 v865 package
(228 MB, 20112 names, 59277 exports). UELib (UE Explorer 1.6.2 DLL) loads it fine (`LoadPackage` + `InitializePackage`);
decompile works for script functions. Helper C# tools live in tools\work (gitignored): dc.cs (decompile by name), sc.cs (grep bodies).
Plain header = summary fields XOR-decoded; the tail after the chunk table (package source, 208 texture allocations) is plaintext in the original.

## Where movement input is zeroed
`KingdomPlayerInput.PlayerInput()` (script, runs every tick on the client):
```
if (Outer.WorldInfo.GRI == none || !GRI.bMatchHasBegun || Outer.IsMoveInputIgnored())
    { aForward = 0; aStrafe = 0; aUp = 0; }
```
Look input has the same test with `IsLookInputIgnored()`. `CatchDoubleClickInput` also needs `!IsMoveInputIgnored()`.

So walking needs ALL of:
1. `WorldInfo.GRI` exists on the client (the replicated KingdomGameReplicationInfo actor).
2. `GRI.bMatchHasBegun == true` (replicated variable of GameReplicationInfo; server side set by `GameInfo.StartMatch`, which sets bWaitingToStartMatch=false).
3. `PlayerController.IsMoveInputIgnored()` is false. It is native (no script body); in stock UE3 it returns `bIgnoreMoveInput != 0` (or cinematic mode).

## What sets / clears bIgnoreMoveInput (script side)
- Sets 1: `Spectating.BeginState`, `ResetViewTarget`, `ToggleGodView`, `IgnoreSomeInput(true)`, `LostControl` (stun), `KingdomChallengePlayerController.PlayerTick` (when Game.IsChallengeEnd).
- Clears 0: `IgnoreSomeInput(false)`, `BackInControl`, `CatapultsGodView`, `SetCinematicMode` (`IgnoreMoveInput(bCinematicMode)`), `ResetPlayerMovementInput`.

## Receiving side of "match started"
- `KingdomGameReplicationInfo.ReplicatedEvent('bMatchHasBegun')`: when it becomes true the client does SetViewTarget(Pawn), ResetCameraMode, `WorldInfo.NotifyMatchStarted()`, StopMovie. `MatchMovieTime >= 3` shows the countdown HUD.
- `IsGameStartedForClient` is a plain bool on KingdomSyncPlayerController, only used by HUD (countdown, tips, formation panel); not part of the move gate.
- Native, no script body: `KingdomSyncPlayerController.IsBattleStarted`, `KingdomChallengePlayerController.SyncReqGameStart` (client->server request, called from ChallengeBeginsAgain), `PlayerController.IsMoveInputIgnored/ResetPlayerMovementInput` base.
- `Event_OnStartFight` (KingdomFlashInterface) is UI only; called from DaTaoSha game Tick.
- `ProcessMove` in the Kingdom PlayerWalking states has no input-ignore check (only sprint/weapon logic).

## Conclusion
Most likely gate: **GRI.bMatchHasBegun**. In a real server it flips true via the GRI actor replication when the server's `GameInfo.StartMatch()` runs after the lobby/countdown. A Sync Cmd name for it is not in script (the set is done by native replication/Sync handlers; `SyncReqGameStart` is the client request, the server answer is unknown native). To check on the fake server: make the GRI's bMatchHasBegun true in the first replication bunch (or whatever message the server sends that triggers `StartMatch`), and ensure the pawn is not in Spectating (bIgnoreMoveInput=0).


