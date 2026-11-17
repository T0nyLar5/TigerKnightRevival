# Agent Guide: read this first

Find docs via notes\INDEX.md (map of every note: read this when ...). History and open problems: notes\HISTORY.md.

Project: revive the shut-down game **Tiger Knight** (Steam 415660) for the owner's solo play, using local fake servers.
The user is not a programmer. User-facing text (guides, .bat banners, console messages) is in simple **Traditional Chinese**.

## Hard rules
- **.bat files must be pure ASCII with CRLF line endings.** Put any Chinese text in a UTF-8 .txt under `server\text\` and show it with `type`. Never `echo` Chinese inside a .bat (it shows as garbage). Check with `file x.bat`, which must say "ASCII text, with CRLF line terminators".
- The game dir `C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight` is **read-only**. Never run game executables; the user tests.
- Python: always `tools\.venv\Scripts\python.exe -I`. Never `python`/`python3` (Windows Store stub, does nothing). Install packages only into that venv.
- Before finishing: stop **every** background process you started. Verify nothing listens on 3010-3019 or 7777:
  `powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort 3010,3011,3012,3013,3014,3015,3016,3017,3018,3019,7777 -ErrorAction SilentlyContinue"`
  (Leftover processes have blocked user tests before.)
- `server\data\player.json` is the user's real save. Back it up before changing it, and restore it after self-tests. Regenerate it only via `tools\unlock_all.py`.
- Never write the Steam ticket (`psw`) into notes or logs, and never send player data to external AI (`tools\ask_llm.py` refuses it anyway).
- Commit only your own files: `git commit`. End the message with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Token budget:** never read a whole file over ~200 lines or a whole log; grep/head with limits first, read only the needed range, cap command output (`| head -40`). Never dump player.json, cfg tables or Ghidra output in full. Reports under 20 lines.
- After a milestone or a user test result, append 1-3 lines to `notes\HISTORY.md` (not every small step).
- **Reports:** write full findings to `notes\reports\YYYYMMDD_HHMM_<topic>.md` (evidence, addresses, code excerpts, dead ends) and commit it. Your final reply is only a short summary (under 12 lines): conclusion, confidence (verified / likely / guess), evidence locations (file:line, exe address, commit), and the report path. No raw tool output in the reply.
- Mark claims as **verified** (seen in real test/log) or **hypothesis** (static analysis) in notes, so later agents don't re-research or trust guesses.
- Stay inside the task's scope. When something can't be resolved with reasonable effort, ship a best guess plus verbose logging and report it. Real test data beats long static analysis.

## Lobby facts (Pomelo, `server\lobby.py` + `server\handlers.py`)
- The hosts file maps `front1-hk.tk.99.com` to 127.0.0.1. The client uses TLS 1.2 without verifying the cert, on one of ports 3010-3019 (usually 3015).
- Handshake reply `code:200`. **Every route reply uses `code:0` for success.**
- **Any key the DLL indexes into must be an object or array (or omitted), never a scalar.** A scalar there crashes PoClientDLL (NULL deref).
- Real requests can differ from guesses: e.g. `subMode` arrives as a list `[0]`. Always tolerate type variations.
- The init chain has 23 flags; see `notes\lobby\login_flow.md` §3b. Rank replies must echo `nation`.
- Unknown routes get `{"code":0}` and are logged as `UNHANDLED`.

## Battle facts
**For battle work, read `notes\battle_state.md` (the condensed current state, under 10k chars) instead of the long notes.** Open the `battle\` and `re\` files it lists (see `notes\INDEX.md`) only for a specific detail. When you learn something new, update `battle_state.md` and keep it under 10k chars.
- mapId 17 is the training ground (建業校場); see `notes\map_ids.md`.
- The lobby push `gameStartup` (after `matchHandler.joinMatch`) makes frontend.exe launch the UE3 exe. A direct launch fails because ParentWnd is required.
- mapId 17 is the training ground (建業校場). mapId 1 is SyncTest, which is not shipped.
- The user must turn OFF 網路優化 (newudp) so the battle uses TCP 127.0.0.1:7777.
- Stream: XOR keystream, per direction, with the counter starting at 0. Frames are `u16 len (incl. header) | u16 type | body` (LE). Confirmed with real traffic.
- Client sends: 0x3e9 MsgConnect {1, playerId, 1, token}, then 0x3f4 "[Win64]", then 0x279c every 5 s while it waits on the loading screen.

## Where things are
- `notes\`: protocol notes, decompiled Lua (`notes\scripts\`), decrypted configs (`notes\decrypted\`), crash analyses.
- `tools\`:
  - crypto: `tkcrypt.py` (Server.dat-style), `uecfg.py` (UE .bin configs).
  - DLL schema dumpers.
  - capstone helpers.
  - `ask_llm.py` (Gemini/DeepSeek for bulk text).
  - `ghidra_12.2_PUBLIC\` (headless decompiler; see `notes\ghidra_usage.md`).
- config.cfg / config_client.cfg / terrain.cfg are CRACKED (2026-11-05): `tools/cfgdec.py`, tables in `notes/decrypted/cfg/` (soldiers, hero_type, armytype, mapindex, agentparam, aiplayer ...). See `notes/re/config_tables_1105.md`. Battle variants 7-9 are the current best bet (test 7 first).
- User launchers in the repo root:
  - 3 = fake lobby;
  - 6 = battle server.
  - `一鍵測試.bat` starts the lobby and the battle server; `一鍵測試_選版本.bat` does the same with `--variant N`; `一鍵關閉.bat` stops everything, including the battle exe.
  - Obsolete files (the old probes, launchers 1/2/4/5) were moved to `_待刪除\`, which is gitignored and for the user to delete. Don't use them.
- Ghidra in parallel: set `TK_GHIDRA_PROJ` to a private copy of `tools\ghidra_projects` (e.g. `tools\ghidra_projects_a`) so agents don't collide on project locks.
- After a user test, run `tools\summarize_logs.py` (about 15-40 lines) instead of reading raw logs.
- `tools\battle_timeline.py [log] [--from S --to S --only 0x2754 --max-lines 60]`: compact per-second battle log timeline with message names (see `notes\battle\msg_dictionary.md`).
- Ghidra 12.2 uses the JDK 25 at `tools\jdk25\` (portable, extracted from the official Adoptium MSI; the system Java stays 21).
- `tools\decompile.py` works (fixed: it now sets `JAVA_TOOL_OPTIONS=-Dapplication.settingsdir/cachedir` to `tools\ghidra_home\`; the default %APPDATA% Felix cache broke startup).
  - `tools\.venv\Scripts\python.exe -I tools\decompile.py "<game dir>rontendinrontend.exe" 0x971a00 [--xref ...] [--out f]`. First call imports+analyzes (~6 min); later calls ~5 s. Details: `notes\ghidra_usage.md`.