# Battle launch: lobby-triggered launch and TCP option (section 9)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [launch_flow.md](launch_flow.md) (table of contents).

## 9. Lobby-triggered launch (2026-11-04)
**"非法启动游戏 / 请使用FrontEnd启动游戏"** [C, Kingdom-Win32-Shipping.exe WinMain 0xd37e42 -> check fn 0xd30c90]: the UE3 exe requires `ParentWnd=<HWND>` in its command line and the value must be a live window handle (IsWindow-style call on it). Direct launch has no ParentWnd, so it always shows the dialog. (`5_...bat` therefore cannot work; adding ParentWnd=<some real HWND> would only embed the game in that window, untried.)

**Trigger**: main menu mode button 「挑戰訓練」 (PushBtn_FlashManMode, MainMenu_RightLayout.lua "打开挑战训练") then the big 「出戰」 button (MainMenu_RightLayou_StartFight) -> Lua `JoinTutorialMatch_lua(1, n)` -> request `matchHandler.joinMatch` {mode,process,...}. Other single modes' 出戰 also send joinMatch and get the same push. PVE epic: createPveBattle then startPveBattle also pushes.
**Server**: reply `{code:0}`, then (after the response) push `gameStartup`:
`{"msgs":[{"playerInfos":[{"roleId":"10001","name":..,"camp":1,"heroType":0,"armyType":0,"sname":"","vip":0}],"addr":[{"ip":"127.0.0.1","port":7777}],"process":1,"subMode":0,"gameMode":1,"token":12345,"playerId":10001,"camp":1,"mapId":1}]}`
Nesting [C from DLL parser 0x10011f9b, `msgs` array; a non-array `msgs` makes the DLL wrap the root, so flat also parses]; roleId/name/sname/ip are strings, all others uint. mapId=1 is a guess [G] (mapindex.txt is encrypted; tutorial map file is TA_XinShouJiaoXue_133_MH).
**TCP**: `newudp` is a CLIENT-side player config (SetSharpness.lua, checkbox "OpenUdp"; "1"=UDP/KCP default, "0"=TCP via `Lua_SetUseTCP`), not sent by the lobby. Cannot be set server-side; user must untick the UDP option in the graphics settings (settings page), or else the battle exe omits `-bTCP` and speaks KCP/UDP (battle_probe also listens on UDP and will log it).
**Map ids**: see `notes/map_ids.md` (mapindex decoded indirectly via map.ani + DefaultGame.ini; mapId 1 = SyncTest which does not exist; gameMode 1 -> 11, 4 -> 12, 5 -> 17).
Unverified: whether the frontend needs extra state (e.g. matched-room flags) before OnNotifyGameStartup accepts the push; whether the process launches with the guessed map.
