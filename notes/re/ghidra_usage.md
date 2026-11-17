# Ghidra headless usage (for agents)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

STATUS: **working**. JDK 25 lives in `tools\jdk25\`. decompile.py sets `JAVA_TOOL_OPTIONS` with
`-Dapplication.settingsdir` / `-Dapplication.cachedir` pointing to `tools\ghidra_home\` (the default %APPDATA% dir made
Felix fail with "data file must be inside the data dir"). First run on frontend.exe: ~6 min (import+analysis);
later decompiles: ~5 s each. Heap is 8G (GHIDRA_HEADLESS_MAXMEM); Kingdom-Win32-Shipping.exe is already imported (Win32). Re-delete `tools\ghidra_projectsrontend_exe.*` if an import was aborted.

## Call
    tools\.venv\Scripts\python.exe -I tools\decompile.py <binary> <addr|name> [more...] [--out file]
    tools\.venv\Scripts\python.exe -I tools\decompile.py <binary> --xref <addr|name|string> [--out file]
- addr: hex VA (`0x180001000` or `180001000`); the function containing it is decompiled.
- name: exact symbol (exports too), else substring match on function names (max 5).
- `--xref`: references to an address/symbol; if nothing resolves, searches defined strings (max 10 hits, 60 refs each).
- First call imports + auto-analyzes into `tools\ghidra_projects\` (slow, minutes for big exes); later calls use
  `-process -noanalysis` (fast). Delete `tools\ghidra_projects\<name>_*` to force re-analysis.
- Java script: `tools\ghidra_scripts\TkDecomp.java` (Ghidra 12 headless has no Jython; Java scripts compile with the JDK).
- Gotcha: `analyzeHeadless.bat` breaks on `(x86)` paths, so the binary is copied to `tools\ghidra_projects\_in\`.
- Output is plain C text on stdout (or `--out`). Image base is whatever Ghidra picks (usually the PE preferred base).
