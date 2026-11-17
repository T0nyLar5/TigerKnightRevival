# Lobby login flow: transport, auth and entry (sections 1-2)
> rev 2 | 2026-11-08 02:35 | faces: client reads 56 not 14 (see reports/20261108_0235)
Part of [login_flow.md](login_flow.md) (table of contents). Covers the KEY FACT, transport, auth and entry routes.

Source: notes/lobby_protocol.md lines 1-98 (sections up to 4) (text moved unchanged, split 2026-11-06).


Sources: Lua UI (decompiled, `notes/scripts/`), `PoClientDLL.dll` (libpomelo2 + the whole game protocol codec: jsoncpp request builders and one giant
response switch), `frontend.exe` (OnLogin/OnAuth handlers). Tools: `tools/dx.py`, `fnkeys.py`, `cases.py`, `jsonkeys.py`, `schema.py`, `routemap.py`.
Scripts decompiled with unluac 1.2.3.569 (`tools/bin/unluac.jar`, downloaded from the sourceforge unluac "latest" link). Bytecode is Lua 5.1, so most of the 237 .lua files in
`frontend/bin/data/ui` are luac; a few (e.g. `LuaScript/ServerEnum.lua`) are plain GBK text and were copied as-is. Output: `notes/scripts/` (5 MB).
Tags: [C] = confirmed from code or capture, [G] = guess.

## KEY FACT: success is `code: 0`, NOT 200 [C]
The DLL reads `code` as int, **default 1 if absent**, and passes it straight to the frontend. `OnAuth` / `OnLogin` test `code == 0` for success.
(The Pomelo handshake reply still uses 200.) Replying `{"code":500}` gave `OnAuth result:500 size:0` (coordinator capture) which is the error path.

## Transport [C]
TLS 1.2 raw TCP, handshake `{"sys":{"type":"desktop","version":"0.3.5-release"}}`, reply `{"code":200,"sys":{"heartbeat":10,"useDict":false}}` works.
Do not send `protos`/dict. Route table: `notes/route_table.txt` (244 routes; route index = response switch case index). Replies only need the request id.

## 1. connector.entryHandler.auth (request id 1)
Request [C]: `{"name":"<SteamID64 decimal>","psw":"<hex of Steam auth session ticket, placeholder>","type":"steam","version":"1.1.111"}`
(non-steam build: type "nd", name/psw = user/password; optional `macaddr`, `ext` are not sent by the steam client). The server need not validate the ticket.

Response (DLL case 2 -> `OnAuth(code, uid, accounts[], count)`) [C]:
```
{ "code": 0,                         // int, 0 = OK
  "uid":  "<string>",                // account uid
  "accounts": [                      // 0..3 roles (RoleSelection UI has 3 slots)
    { "tp": "hk",                    // string area: "hk" | "eu" | "na" (shown as area text)
      "uid": "<role uid string>",    // used in the entry request
      "name": "<string>",            // role nickname
      "level": 1, "sex": 0, "gold": 0, "score": 0, "copper": 0, "generalexp": 0, "exploit": 0,   // uint
      "sname": "<string>",           // syndicate name
      "faces": [0,0,...],            // uint array (56 entries read, cmp 0x38)
      "vipvalidtimesec": 0, "native": 0, "faceicon": 0, "faceframe": 0,
      "suit": 0, "shoes":0,"helmet":0,"armor":0,"shawl":0,"horse":0,"saddle":0,"hoof":0,"strike":0,"horseadd":0,
      "weapon1":0,"weapon2":0,"weapon3":0,"weapon4":0,"fashion":0,"fashion1":0,"fashion2":0,"fashion3":0,"fashion4":0,
      "fashion5":0,"fashion6":0,"fashion7":0,"banner":0,"markflag":0 }
  ] }
```
Each field is read as "if present and convertible, else 0/empty", so a minimal account works: `tp, uid, name, level, faceicon`.

Frontend behaviour [C]:
- code == 0 and accounts count <= 1: the client immediately sends `entry` itself (count 0 uses the top-level `uid`, count 1 uses accounts[0].uid). No role UI.
- count > 1: Lua `On_Auth(nRet=0)` -> role selection screen -> Enter -> entry with the chosen role.
- code != 0: Lua `On_Auth(nRet=code)` shows an error box. ELogin (`LuaScript/ServerEnum.lua`): 1 server error, 2 restorable, 3 bad user/psw, 4 account not active,
  5 forbidden, 6 repeat login, 7 version mismatch, 8 login queue, 9 anti-addict; 10 other.
- If the account has no role: tutorial / role creation flow (`BeginCreateRole`, route `userstate.userHandler.newUser`, Lua `CreatRoleComeBack` nRet 0 ok, 1..6 errors) [G for details].
- Before auth, Lua gets `On_Login_Server(nRet=1)` when the connection is up; that is what triggers `LoginUser` (auth).

## 2. connector.entryHandler.entry
Request [C]: `{"uid":"<role uid>","name":"<steamid64>","psw":"<ticket hex>","type":"steam","version":"1.1.111"}`
Response (DLL case 3 -> `OnLogin(code, uid, restore, csid, forbidtime, chatnum[])`) [C]:
```
{ "code": 0, "uid": "<role uid>", "restore": false,   // bool: a restorable (in-progress) battle exists
  "csid": 1,                                           // int, default 1
  "forbidtime": 0,                                     // int, unix secs login ban (surfaced as IntoGameSucess nParam1)
  "chatnum": [0] }                                     // int array
```
On code 0 the frontend fires Lua `IntoGameSucess(nRet=0)` and starts data loading. code 8 = login queue (`Longin_Queue` UI) [G on push `loginWait`]; other nonzero: error, auto logout after 3 s.
