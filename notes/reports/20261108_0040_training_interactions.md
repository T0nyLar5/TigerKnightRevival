# Training ground interactions (posts / block hint / NPC challenge teleport) - 2026-11-08 00:40
Task: why attack-direction post hints are odd and why NPC challenge choice does not teleport. Static + log analysis, no game run.

## Log census (server\logs\battleserver_20261108_000608.log, ~10 min of play; _001252 is a 1-min connect-only run)
Client msgs after spawn, ALL answered by "unhandled, logged only" except 0x4e3e echo: 0x2737 x2699, 0x2721 x2616, 0x2754 x1239 (bodyturn), 0x2738 x630, 0x4e3e x179 (echoed), 0x2739 x77, 0x2722 x67, 0x2732 x49, 0x272f x49, **0x2774 x9, 0x2750 x3, 0x275e x5, 0x273e x8, 0x2735 x8, 0x2736 x8, 0x272b x1**.
Interaction-relevant ones (verified in log):
- **0x2750 MsgReqTutorialStep** body `uid, step`: steps 0x0f (00:10:12), 0x10 and 0x11 (00:12:02-03, right after a 0x272b `00 cf 00`). First time ever seen (earlier note reports/20261107_0900 said never sent). Server never replied.
- 0x2774 = ContinusCut (combo-cut direction): body `uid, 02, dir 0..3` (SyncClient 0x100c89b0 / 0x100c8ab0 log "ContinusCut_2nd/3rd Dir: %u"). Attack-direction chain; server never replies.
- 0x2735 (uid, 2/4/6/0) / 0x2736 = attack/block direction start/end (meaning H).
## Static findings (Win32 SyncClient.dll, hypothesis)
- Sender FUN_100b0cd0: builds 0x2750 (uid, byte step), only if mode (this+0x40) is 0, 4 or 0xb, then calls local FUN_1000d230(step) (client applies step locally too).
- Receiver: top-level Cmd **0x4e93 CmdSyncTutorialStage**, codec FUN_10074140: two uvars (a, step); dispatcher case 0x3f in FUN_100ae390 -> FUN_100b3740, which uses step (field at +8) and ONLY acts if mode (+0x40)==0xb, else logs "SyncClient::SetTutorialStep Not Tutorial Mode !". FUN_1000d230: steps 8, 10 and 0xb-0xe have special effects in tutorial mode.
- Step values seen (0xf-0x11) are outside the 0xb-0xe range handled in FUN_1000d230 -> the training flow's step ids are server-owned; the original server tracked stage and answered. Our server never answers => client state machine (hint arrow order, post respawn, block-vs-attack hint, NPC teleport) is left half-driven. Confidence: medium-low that this alone fixes it.
- Posts/dummies/NPC dialogs are UE3 script actors (ChallengeGame_Dummy/NPC, KingdomChallengeGame.SetAndPopupTargets, OnDummyWrongHit, notes/research/research_ai.md section 5). Teleport after the NPC choice is probably a server Cmd (position set) or stage change; no client request for it was seen in the log (no challenge-start Req besides 0x2750/0x272b?). 0x272b `00 cf 00` is unknown (maybe challenge select; cf=207).
- The real mode (+0x40) of our session is unknown (gameMode=5 sent in gameStartup; the sender gate accepts 0/4/0xb so the client is NOT in a different mode, else it would not have sent). If it is 0, the reply is ignored harmlessly.
## Fix shipped: variant 43 (server/battle_server.py)
V37 behaviour (internally VARIANT=37 via TUT flag) + reply to every 0x2750 with top-level Cmd 0x4e93, body = request body verbatim (uvar uid, step). Low risk. py_compile OK, game not launched. Menu line added in server\text\variant_menu.txt.
Test: variant 43, map 17, walk helper as usual; go to the NPC, pick a difficulty; hit posts. Look in the new battle log for "v43 REPLY" lines and whether the hero teleports / hint order changes.
## Next if no effect
Decompile 0x272b sender (dll offset search for bytes `04 00 2b 27`), 0x275e (SyncClient 0x10054f37), and the receiver cases for 0x4ebc ChallengeMatchResult; ask for a log of the hint arrow sequence with the unhandled 0x2735/0x2774 timestamps.
