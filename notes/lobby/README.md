# Lobby guide (Pomelo JSON protocol)
> rev 2 | 2026-11-08 02:22 | added pointer to pre-battle troop selection (Combat_Readiness) + new handlers

This folder covers the fake lobby: the Pomelo JSON protocol between PoClientDLL / frontend.exe and `server\lobby.py` + `server\handlers.py`. It covers the login and entry flow, the data loading that must finish before the lobby screen opens, push events, and the unlock-all state. The short rules are in `AGENT_GUIDE.md` ("Lobby facts").

Which file to read for which question:
- `login_flow.md`: table of contents only. Start here to find the part you need.
- `login_flow_auth_entry.md`: read when auth or entry fails, or to check `code: 0` success, the account and role shape, and the sources and tags.
- `login_flow_data_loading.md`: read when adding or checking the reply shape of a route used during data loading.
- `login_flow_init_and_push.md`: read when the loading screen stalls at a step (the 23-step init chain, the `nation` echo) or when a push route is in question.
- `state_and_actions.md`: read when adding or fixing a lobby route, the unlock-all state (`tools\unlock_all.py`), help panels, the max level, the soldier-tree freeze fix, or known route gaps.
- `../reports/20261108_0222_prebattle_troop_select.md`: read when working on the pre-battle troop window (joinMatch -> matchRoomPrepareInfo -> prepareMatchRoom -> gameStartup), `TK_PREBATTLE`, or what `soldier:` in the client log means.
- `../route_table.txt`: read when you need a route number (the index of the 244 routes, used by `tools\schema.py`).
- `../crash/analysis.md`: read when the client crashes inside PoClientDLL (scalar where the DLL indexes).
- `../client_log_first_login.txt`: evidence only (first successful login, 2026-11-04). Never read it whole.

Status: login, entry and the full init chain work with the fake lobby (first login 2026-11-04); remaining work is the route gaps listed in `state_and_actions.md`.

Status (2026-11-08): character creation works (`一鍵測試_捏角色.bat`); the name is saved; the 3D model appearance is not applied yet (see `../reports/20261108_0300_appearance_all_items.md`). All items in the warehouse work (`tools\unlock_all.py --all-items`, 1283 rows).
