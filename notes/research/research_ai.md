# Research: AI-controlled players / bots (2026-11-05, ~7 min, ~33 decompile/xref calls, private Ghidra project b)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Verdict: **AI EXISTS LOCALLY in SyncClient.dll (the client runs it). The server does not compute AI inputs, but it must (a) create the AI unit via the normal player/creature messages, (b) send a "Control" message that hands the unit to a client, and (c) relay that client's Req* output to everyone.** Confidence: high that the AI code is in the client; medium that the delegation message is 0x4e4a as described; low-medium on the exact end-to-end sequence (never run).

## 1. What exists (strings/RTTI, SyncClient.dll Win32; Sync.dll only holds the config names)
- Namespace `ai::` in SyncClient: AIBase, AIPlayer, AIDtsPlayer, AISoldier, AIFujiang (lieutenant), AIBoss, AIHorse, AIAnimal, AIMonster* (Challenge, Patrol, Formation, Block, ThrowStone, McCata/McBallista, OneOnOne, SpecialTarget, RollWood), AIOrder{Base,Defend,Follow,Push,Animal,Monster}, AIFormation, AIMorale{Normal,High,Low,Collapse}, ~45 AISoldierSkill*, AIWeapon* (melee/bow/crossbow/throw, ground/ride), AIPlayerAction{EnemyPlayer,Fortress,SelfBoss,EnemyBoss,Rescue,FinalHit}, AiPersonalSkill_*.
- AIPlayer::UpdateCmd = `0x100ff9e0` (vtable `0x102665c0`, ctor `0x100ff540`, object 0xf8 bytes). AIFujiang vtable `0x10267514` (ctor `0x10111060`), AISoldier `0x10267458` (ctor `0x1010f8d0`), AIMonster `0x102667f4`.
- Configs (packed, not on disk): `config\aiplayer.txt`, `aiplayer_dts.txt`, `config_client\aiplayeraction.txt`, `aisoldiericon.txt`, `config\agentparam.txt`, `aiskill1..43_*.txt`, `aipersonalskill.ini`, `config\challenge_tutorial.ini`, `config\pve_monster.txt`, `config_server\monstercreater_*.txt`, and `config_server\botnames.txt`, `config_server\botequip.txt` (server-side bot names/gear; Sync.dll static init 0x1007f0b0 only registers BotNamesData).
- Unit classes come in pairs: `*Ctl` (controlled/local: PlayerCtl, SoldierCtl, FujiangCtl, BossCtl, HorseCtl, PveMonsterCtl, AnimalCtl, McXxxCtl) and `*Mir` (mirror/remote). AI drives Ctl units.

## 2. How a unit becomes AI-controlled
- SyncClient message structs: `MsgCmdControlSoldiers, ControlHorses, ControlBoss, ControlPveMonster, ControlPveMonsterGroup, ControlAiPlayer, ControlAnimal, ControlMc` and `MsgCmdRemoveControl*`, `MsgCmdRemoveAgent`, plus `MsgCmdAiPlayerSoldierSkill, MsgCmdAiFormationMass, MsgCmdTroopMove, MsgCmdChangeCommand`. These are server -> client delegation messages: "you now run the AI for these units".
- **MsgCmdControlAiPlayer = type 0x4e4a**, body = a single `uvar uid` (deserializer `0x10067fa0`, registry entry in `0x10093050`; struct = {header word 0x4e4a0004, u32 uid}). Found via RTTI: sp_counted vtable `0x1021bff4` -> make_shared `0x10067e90` -> `0x10067f30` -> registry. Other Control* ids not mapped (probable range 0x4e46..0x4e4e, deserializers `0x10067840 / 0x10067a10 / 0x10067bf0 / 0x10067dc0 / 0x10068160 / 0x10068330 / 0x10068510 / 0x100686f0`).
- Client handler: `0x1000b2e0(msg)` (msg+4 = uid): looks the uid up in the message-pipe map and RTTI-casts to **PlayerCtl** (so AddPlayer 0x4e22 must have run first, see battle_launch.md step 5). If the sync-mode field `(this->+8)->+0x10 == 0x13` it takes the "DTS player" path (this+0x88, AIDtsPlayer); else it creates the AI manager (this+0x68) and calls `0x10005e60(uid)`, which allocates `ai::AIPlayer`, registers it and calls `playerCtl->(+0x48)->vcall+0x40(1)` (AI enable). Soldier/horse/boss analogue: `0x100b9620(uid)` switches on unit kind: 1 -> `0x100b9ce0 / 0x100b9ec0` (AISoldier), 4 -> `0x100ba420`, 5 -> `0x100ba250` (AIFujiang).
- So "AI-controlled" is NOT a field in AddPlayer/AddPerson; it is the separate Control message. AddPlayer ptype is 0/1/2 (normal/pending/watcher), isSelf=0 for a remote hero.
- AIPlayer::UpdateCmd also tests mode flags `0x13` and `0x2f` (vcall +0x8c on the sync client; probably game-mode ids, maybe tutorial/challenge): meaning unknown.

## 3. Local or server-driven?
- Decisions (target choice, pathfinding "AI[%u] Find Path", skills) run locally in the controlling client. Output goes through the normal unit-controller interface, i.e. the same `MsgReq*` messages a human generates (`MsgReqMove`, `ReqMoveActionStart/End`, `ReqAction`, `ReqChangeCommand`, `ReqDoSoldierSkill`, `ReqTroopMove`, `ReqAssaultAttack` ...; medium confidence, not decompiled). The server accepts them and rebroadcasts the matching `MsgCmd*` / frame messages to all clients, as for a human. No per-frame AI input generation on the server.
- Caveat: AI needs PlayerCtl/SoldierCtl, configs (hero ids, aiplayer.txt rows) and map data (nav is local). Config ids are still unknown (config.cfg encrypted), so unit `kind` values are guesses.

## 4. Fallback: server-generated inputs
The server would emit slave per-unit messages (Sync.dll dispatch `0x10034630` / `0x100348c0`, first field = uid, ids 6..0x1a0) for movement/attack. Their layouts were NOT decoded here. Creation layouts: battle_launch.md steps 3-5 (slave msg 1/2/3/4; top-level 0x4e22, 0x4e80). A scripted server bot is the larger job; prefer the Control route.

## 5. Tutorial / training (mapId 17, gameMode 5 challenge)
- Dummies/targets are **UE3 script actors in the map**, not network-spawned: `ChallengeGame_Dummy` (CheckDummyBroken), `ChallengeGame_NPC`, `KingdomChallengeGame` natives `RespawnDummy`, `SetAndPopupTargets`, `OnDummyDown`, `OnDummyWrongHit`, `OnTargetDown`, `OnTimberStakeDown`, `SetTutorialStep`, `GetMatchResult`; `KingdomChallengePlayerController::HitDummy / ShootTarget / BlockStageTakeHit`. Stage 1-3 style content (stakes, targets) needs no server spawn.
- Stage 4 uses AI monsters: `ai::AIMonsterChallenge` / `CliTutorialChallenge` (SyncClient) loading `challenge_tutorial.ini` stages 1-5. Stage progress is a server message: `MsgCmdSyncTutorialStage`, `MsgReqTutorialStep` (log "SyncClient::SetTutorialStep Not Tutorial Mode"), scores `MsgReqChallengeStageOne/Two/Three/FourScore`, `MsgReqChallengeMatchEnd`. Stage-4 monsters probably come via ControlPveMonster or CliTutorialChallenge local creation (not verified).
- Lua `notes/scripts/ui/Addons/TutorialMode/SpecialMode.lua` reads the same ini via `GetBinariesIni("challenge_tutorial","Stage"..i)` (UI side only).

## 6. Proposed approach
1. Get the human hero working first (variants 5/6). Check whether training map 17 is playable with no bots (dummies are local).
2. Bots: per bot send top-level `MsgCmdAddPlayer 0x4e22` (isSelf=0, uid=2000x, name from botnames) + slave AddPlayer + `MsgCmdReBorn 0x4e80`, then `MsgCmdControlAiPlayer 0x4e4a {uid}` to the human client. Watch the log (`RECV [after spawn]`) for MsgReq* carrying the bot uid; then add a relay echoing them to all clients as the matching Cmd/frame messages.
3. If 0x4e4a is ignored (mode 0x13 path, etc.), decompile `0x1000b2e0` fully and `0x100f86f0` (AIBase ctor), and map 0x4e46..0x4e4e names to find ControlSoldiers for troops.
4. Troops need soldier type ids from the encrypted config: same blocker as before.

## Unknown
- Ids of the other Control* messages; whether AI Req output is applied locally before the server echo; meaning of modes 0x13/0x2f; contents of aiplayer.txt.
