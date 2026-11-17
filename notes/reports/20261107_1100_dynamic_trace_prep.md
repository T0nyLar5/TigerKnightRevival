# Dynamic trace prep (2026-11-07 11:00)
Goal: find the native instruction(s) writing hero Location/Velocity each tick while W is held (Cheat Engine, then Ghidra Win64).

## Done
- Key H in `英雄速度檢查.bat` -> `tools\ue_inspect.py --addr` (read-only). Prints absolute addresses: Pawn, Controller, Location.X, Velocity.X, Acceleration.X, Physics byte, module base. Also saved to `server\logs\pawn_probe_last.txt`. Menu line in `server\text\probe_menu.txt`. Selftest (mock) OK; not run against the real game (verified offline only).
- Guide for the user (Traditional Chinese): `notes\使用說明_CE追蹤.md` (copy: `server\text\ce_trace_guide.txt`). Steps: key H, CE as admin, attach, Add Address Manually (Float), "Find out what writes", hold W 5 s, same for Velocity.X, copy list + module+offset. Includes anti-debug warning (stop + report if kicked/crash) and alternative Edit > Settings > Debugger Options > "Use VEH debugger".

## Ghidra Win64
See the status block at the end of this file.

## From CE "module+offset" to Ghidra
- PE ImageBase = 0x140000000 (verified: `ue_inspect.py --static`, SizeOfImage 0x1c75000).
- Ghidra address = 0x140000000 + offset. Example: `Kingdom-Win64-Shipping.exe+AEE73F` -> 0x140aee73f.
- If CE shows an absolute address instead: offset = address - module base (key H prints the base; ASLR may move it per run), then add 0x140000000.
- Decompile: `set TK_GHIDRA_PROJ=...\tools\ghidra_projects_w64` then
  `tools\.venv\Scripts\python.exe -I tools\decompile.py "C:\Program Files (x86)\Steam\steamapps\common\Tiger Knight\Binaries\Win64\Kingdom-Win64-Shipping.exe" 0x140aee73f [--xref 0x...] [--out f]`.

## Ghidra Win64 status: DONE (verified)
- Imported + analyzed `Binaries\Win64\Kingdom-Win64-Shipping.exe` (source untouched; staged copy in the project `_in`) into `tools\ghidra_projects_w64\` (gitignored via `tools/ghidra_projects_*/`). Took roughly 20-25 min. Test decompile of 0x140aee73f (FUN_140aed840) worked.
- Later calls use `-process -noanalysis` (fast). Do not delete the project dir. If it is ever lost: rerun the decompile command above with `TK_GHIDRA_PROJ` set to the same dir (re-import ~25 min, run in background).
- No background process left running (java checked).
