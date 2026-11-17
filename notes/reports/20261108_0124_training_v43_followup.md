# Training ground V43 follow-up (log battleserver_20261108_011259.log)
## Log facts (verified)
- Session after spawn covers 01:14:37-01:15:10 only. Non-movement client msgs: 0x4e3e x21 (echoed), 0x2722 x13, 0x2732 x5, 0x272f x5, 0x273e x2, 0x275e x1, **0x2750 x1 (step 0x0f, 01:14:49.832)**. Only ONE v43 REPLY (0x4e93 `91 4e 0f`) was sent. No 0x2735/0x2736/0x2774 at all.
- Nothing was sent to the server at the NPC dialog time (only 0x2722/0x275e noise): the dialog and option clicks are client-local; the server was never asked anything.
## Answers
b. HUD pop-ups after EACH post vs a single echo: the echo cannot be the per-post cause (confidence medium-high). Likely client-local KingdomChallengeGame result events with the challenge timer stuck at 00:00 (known open issue "HUD timer 00:00", no TimeLimit): "time over" = challenge failed at once; plausible but unverified (hypothesis).
c. Option text: Localization KingdomGame.CHT (UTF-16) has [KingdomChallengeHUD] StrDifficultyLevel0..2 ("1.簡單模式","2.普通模式","3.困難模式"), StrChallenge0..3 (再次挑戰/離開/進行訓練/挑戰); so strings exist. Blank options means the dialog's option list/data is not populated, probably from a server-supplied challenge record (Cmd 0x4ef4 MsgCmdChallengeTutorialStep, 0x4ebc ChallengeMatchResult, 0x4efe RecordBreak; never sent by us). 0x4ef4 codec = SyncClient 0x10084b50: struct 0xc, one uvar at +8 (+4 header-ish field read by FUN_10092d90); semantic and handler NOT decoded (hypothesis). I did not find the exact strings of the HUD pop-ups in the CHT file (probably GFx/UI package).
d. No safe concrete fix: guessing 0x4ef4's value could fire further result HUDs. No new variant. V43 stays (harmless).
## Next
Decode the dispatcher case for 0x4ef4 -> handler (SyncClient FUN_100ae390 neighbours) and the UE-side native that consumes it; try CmdCountDown with a nonzero running timer (value>0) for challenge timer; ask user for a log that includes clicking each NPC option with timestamps.
