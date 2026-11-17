# Character creation page (捏角色) in the fake lobby

## How the client decides (static analysis of notes/scripts, hypothesis until user tests)
- Login.lua `On_GetRoleState`: `TUTORIAL = tParam.nParam1` (= getRoleState.tutorialStep). `Login_TutorialMode_Force_Complete` (Login.lua:899): if TUTORIAL == 0 -> `LobbyClient:BeginCreateRole()` -> Lua `CreatRoleCreatName` creates CreatRole_Gender / CreatRole_Face / CreatRole_Nation (Login.lua:514). TUTORIAL 1-3 = tutorial screens. `On_RoleStateUpdate` push re-runs it.
- Final button in CreatRole_Nation.lua:249 calls `RegisterRole(name, gender, head, faceData, hair, scars, nation, preview, headId, 0)` -> route `userstate.userHandler.newUser` (route 13); Lua callback 5 `CreatRoleComeBack` nRet 0 = ok, 1..6 errors. Name check route `checkNickName` (24).
- auth with 0 accounts is NOT what shows the page; our auth returns 1 account and the client enters by itself.
- In-lobby editor without a new character: Store disguise/change-face card (Store.lua:4155 `Store_UseDisguise_Yes` shows CreatRole_Gender/Face; PushButton_CreatRole_ChangeFace_Enter -> `Command_ChangeFace` -> route `useChangeFaceCard` (18)). Needs a change-face item in the bag; not verified that unlock_all provides one.

## Implementation
- `server\handlers.py`: env `TK_NEW_CHAR=1` -> getRoleState returns tutorialStep 0 (in memory only, until newUser succeeds; normal mode unchanged, player.json not touched by this). New handlers `newUser`, `checkNickName`, `useChangeFaceCard`: log the raw request (`[newUser] req=...` in the console), back up player.json once to `player.json.before_newchar`, store name/sex and raw request (`created_role_req` / `changeface_req`) in player.json, reply `{code:0}`.
- Launcher `一鍵測試_捏角色.bat` (ASCII+CRLF, text in server\text\newchar_banner.txt): sets TK_NEW_CHAR=1 and starts only the lobby.
- Field names of newUser request are GUESSED (name/sex); real request will show in the console log. Reply shape guessed `{code:0, uid}`; after success the client may expect a roleStateUpdate push or re-login (unknown).

## Self-test
tools\selftest_lobby.py ALL PASSED (normal mode). Ad-hoc client: normal mode tutorialStep 5; TK_NEW_CHAR=1 tutorialStep 0, newUser ok then tutorialStep 5. player.json restored (the selftest itself rewrites it). No listeners left.

## Risks
Unknown whether the 3D face editor scene needs data the lobby does not send (U3Scene); could crash the client -> screenshot/log to agent. To undo: restore server\data\player.json.before_newchar.
