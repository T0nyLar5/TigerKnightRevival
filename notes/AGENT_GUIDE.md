# Agent guide: hard rules (condensed 2026-11-08)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Read `START_HERE.md` first. Project: revive the shut-down game Tiger Knight (Steam 415660) for the owner's solo play with local fake servers. The user is not a programmer; user-facing text is simple Traditional Chinese. Full pre-split text: `archive/AGENT_GUIDE_old.md`.

## Hard rules
- **.bat files: pure ASCII with CRLF.** Chinese text goes in a UTF-8 .txt under `server\text\`, shown with `type`. Check: `file x.bat` must say "ASCII text, with CRLF line terminators".
- **Game dir `C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight` is read-only.** Never run game executables; the user tests in game.
- **Python:** `tools\.venv\Scripts\python.exe -I`. Never `python`/`python3` (Windows Store stub). Packages go only into that venv.
- **Before finishing:** stop every background process you started. Nothing may listen on 3010-3019 or 7777:
  `powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort 3010,3011,3012,3013,3014,3015,3016,3017,3018,3019,7777 -ErrorAction SilentlyContinue"`
- `server\data\player.json` is the user's real save. Back it up before changing it, restore after self-tests. Regenerate only via `tools\unlock_all.py`. Never dump its contents.
- Never write the Steam ticket (`psw`) into notes, logs or replies. Never send player data to external AI (`tools\ask_llm.py` refuses it).
- Commit only your own files: `git commit`, with a blank line then the Co-Authored-By line the session specifies.
- **Token budget:** never read a whole file over ~200 lines or a whole log. Use grep/head/sed with limits, cap output (`| head -40`). Never dump player.json, cfg tables, Ghidra output or the 65 KB `re/protocol_catalog.md`. Reports under 20 lines in the reply.
- **Revision stamp:** line 2 of every note = `> rev N | YYYY-MM-DD HH:MM | <one-line summary of the last change>`. On each edit bump N and REPLACE that line (never accumulate; older history lives in `git log <file>`). Missing stamp: add `rev 1`. Read the stamp before trusting a note; a stale date vs HISTORY.md means check before relying.
- **After a milestone or user test:** append 1-3 lines to `notes\HISTORY.md` (end of file). Not every small step.
- **Reports:** full findings go to `notes\reports\YYYYMMDD_HHMM_<topic>.md` (evidence, addresses, dead ends), then commit. Final reply: under 12 lines (conclusion, confidence, evidence locations, report path).
- Mark claims **verified** (seen in real test or log) or **hypothesis** (static analysis). Do not trust a hypothesis without a test.
- Stay in scope. If a question stays unresolved, ship a best guess with verbose logging and report it. Real test data beats long static analysis.
- After a user test, run `tools\summarize_logs.py` (15-40 lines) instead of reading raw logs.

## Lobby facts (Pomelo; `server\lobby.py`, `server\handlers.py`)
- Hosts file maps `front1-hk.tk.99.com` to 127.0.0.1. Client uses TLS 1.2 without cert check, on one of ports 3010-3019 (usually 3015).
- Handshake reply `code:200`. **Every route reply uses `code:0` for success.** Unknown routes get `{"code":0}` and are logged `UNHANDLED`.
- **Any key the DLL indexes must be an object or array (or omitted), never a scalar.** A scalar crashes PoClientDLL (NULL deref).
- Real requests differ from guesses (e.g. `subMode` arrives as `[0]`). Tolerate type variations.
- Init chain has 23 flags (`lobby/login_flow_init_and_push.md` section 3b). Rank replies must echo `nation`.

## Battle facts
- For battle work read `battle_state.md` (short current state) and only the topic note it points to. Keep `battle_state.md` short.
- mapId 17 = training ground (建業校場); mapId 1 (SyncTest) is not shipped. See `map_ids.md`.
- The user must turn OFF 網路優化 (newudp) so the battle uses TCP 127.0.0.1:7777.
- Stream: XOR keystream per direction, counter from 0. Frames `u16 len (incl. header) | u16 type | body`, little endian (confirmed with real traffic).
- Client sends 0x3e9 MsgConnect, then 0x3f4 "[Win64]", then 0x279c every 5 s on the loading screen.
- **Never send CmdSync (0x4e20): it sticks the loading screen.**

## Where things are
- Tool list and launchers: `tools_map.md`. Notes index: `INDEX.md`.
