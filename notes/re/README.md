# Reverse engineering guide (formats, ciphers, tools)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

This folder holds the reverse-engineering facts that other areas depend on: the Kingdom exe and UE3 config ciphers, the Server.dat cipher, the UE3 `.u` script package format, and how to run the Ghidra decompiler. Battle-protocol facts are in `..\battle\`.

Which file to read for which question:
- `config_tables_1105.md`: read when you need the config.cfg / config_client.cfg / terrain.cfg cipher or the table layout (decrypted tables are in `..\decrypted\cfg\`).
- `kingdom_exe_findings.md`: read when reversing the battle exe (Kingdom-Win32-Shipping.exe, SyncClient.dll), including the UE3 config .bin cipher.
- `server_dat.md`: read when touching Server.dat or langandplatform.dat (cipher cracked, round trip byte-identical).
- `script_packages.md`: read before patching a `.u` file (format, `tools\updec.py`, `tools\upatch.py`).
- `ghidra_usage.md`: read before a decompile (`tools\decompile.py`, Ghidra 12.2 headless, JDK 25 under `tools\jdk25\`).

Tags legend: see `..\battle\README.md`.

Status: the Server.dat and config.cfg ciphers are cracked and verified; the `.u` patch tool builds and round-trips the unmodified file, but the walk mod is still under test (`..\battle\walk_gate_mod_first_test.md`).
