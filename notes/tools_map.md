# Tools map (split from AGENT_GUIDE.md, 2026-11-08)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Paths relative to the repo root. Python: always `tools\.venv\Scripts\python.exe -I`.

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
- Live inspector and walk helper (repo root): `英雄速度檢查.bat` (keys 1-9, A-J), `走路輔助.bat`. Survey of tested movement presets: `battle/movement_params.md`.
