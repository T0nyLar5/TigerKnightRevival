# Battle launch: gameStartup, command line and game classes (sections 1-2)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [launch_flow.md](launch_flow.md) (table of contents).

## 1. Launch flow [C]
- The lobby pushes `gameStartup` (PoClientDLL, JSON, parsed at ~0x10011f9b), or answers `matchHandler.restore` (reconnect) with similar fields.
  `gameStartup` keys [nesting G]: `msgs[]` -> `playerInfos[{roleId,name,camp,heroType,armyType,sname,vip}]`, `addr[{ip,port}]`, `process`, `subMode`, `gameMode`, `token`, `playerId`, `camp`, `mapId`.
- frontend `FLobbyClient::OnNotifyGameStartup` (0x86e1a0; vtable slot 32) logs
  `Address:%s,port:%d,mapid:%d,Camp:%d,PlayerID:%d,Token:%u,gamemode:%u,Subgamemode:%d,Count:%d,selfID:%d,Process:%d,net_line:%d`.
  It uses addr[0] (addr[1] only if a net_line flag is 0 and count>1: send ONE addr). Lua event `MainMenu_Fighting_On_GameStartup` (id 104).
- It then CreateProcessA's `<root>\Binaries\Win64\Kingdom-Win64-Shipping.exe` on 64-bit OS (the "32" in the exe name is replaced by "64"), else Win32. Name comes from a frontend config record. `TigerKnightEnv.exe` is only a DirectX/PhysX/VC dependency installer, not part of battles.

## 2. UE3 command line [C]
`<exe> <MapName>?game=kingdomgame.<GameClass>?ip=<addr>?port=<port>?id=<PlayerID>?map=<mapid>[?forbidtalk=1][?hideselfhelmet=1]?ResX=..?ResY=..?ParentWnd=<frontend HWND>?Token=<token>  -SS:MaxMultiSamples=N -LANGUAGE=CHN|CHT|INT -WINDOWED|-FULLSCREEN -vsync|-novsync -dx9|-dx11 [-NVDOF -NVHBAO -NVAA] [-NOSEEKFREELOADING] [-NOPRELOADCACHE] [-bTCP] [-CHECKTGP]`
- MapName = map file name from `mapindex.txt` (inside config.cfg) for mapid.
- gamemode -> class (jump table 0x8701dc): 1 KingdomTutorialSyncGame; 2 PVE_Crusade/Siege/Fortress/ZhongJun family (by submode; `?bNewBee=1` for submode 0/8 when tutorial stage <=3); 3 PVP_*_SuperStarMode family (submode 0..7); 4 KingdomTaofaTutorialGame; 5 KingdomChallengeGame; 6 KingdomPVEEpicGame; 7 PVP_DaTaoSha(_FreeOrganizeTeam if submode 3); 8-12 PVE_Crusade; 13 PVP_HeroChampionMode.
- Restore and replay use the same format (`?token=`; replay adds `?VideoFileAddress=<file>` and no token).
- `-bTCP` is added when g_bUseTCP is set (Lua `Lua_SetUseTCP`, driven by player config `newudp`: "1" = UDP/KCP (default), "0" = TCP). Use TCP for our server.
- `CreateMapCommandLine:CommandLineFileMap<N>` in the log is NOT the battle command line: N is the frontend HWND, used for shared memory (`ShowCharactorFileMap`, `CommandLineFileMap`, semaphores) with the lobby 3D-character UE3 process (`...XuanRenTEST_04?game=kingdomgame.kingdomCharactorGame`, only when [UNREAL] u3 is on; with u3=0 the lobby uses the internal S3 engine, log `open_s3`).
- The UE3 window is a child of the frontend (ParentWnd) and talks back by WM_COPYDATA (LaunchStep, battleid, DamageData, NOTIFYCLOSEGAMEEXE). Failure to spawn -> request `userstate.matchHandler.clientStartGameFail` {name,sex}-ish [G body].
- Client requests that lead here: `matchHandler.joinMatch` {mode, process (=tutorial number), halfwayjoin, zone, direct, subMode}, `customRoomHandler.startGame`, `matchHandler.startPveBattle`, `userHandler.setTutorial`.
