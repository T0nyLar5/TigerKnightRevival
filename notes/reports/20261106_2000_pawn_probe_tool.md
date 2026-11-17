# pawn_probe: one-click memory probe for hero GroundSpeed/AccelRate (11-06; tool built, NOT yet run in game)

## Tool
- `tools\pawn_probe.py` + launcher `英雄速度檢查.bat` (menu 1 = read only, 2 = read then write fix). Output also saved to `server\logs\pawn_probe_last.txt`.
- Flow: newest battleserver log -> last 0x2737 f32 xyz (same decoding as battle_moves.py) -> attach Kingdom-Win64-Shipping.exe (fallback Win32 name) -> scan committed MEM_PRIVATE RW pages for the exact 12-byte triple (all 6 axis orders, scales 1/100/0.01) -> in +-0x800 bytes of each hit look at every 4-aligned 6-float block (GroundSpeed, WaterSpeed, AirSpeed, LadderSpeed, AccelRate, JumpZ). Filter: all floats finite 0..20000 and JumpZ (6th) 100..2000. Score: +2 JumpZ==600 (fPlayerJumpZ), +2 any of AccelRate 2048/4096, GroundSpeed 440/450/600, +1 all five zero, +1 all five 0 or 1..5000. Top 20 printed.
- Fix mode writes ONLY: GroundSpeed(+0)=450, AirSpeed(+8)=450, AccelRate(+16)=2048 floats at the chosen candidate (asks which; Enter = #1, n = cancel), reads back.
- Errors (Chinese): log missing / no 0x2737; game not running; OpenProcess denied -> run .bat as administrator.
- Tested offline only: py syntax, selftest on fake buffer (`--selftest`, finds a zero block + 600 near a permuted triple), log parsing on battleserver_20261106_180447 (last pos 0.91,4.17,-0.28; that user was mid-jump, hence user must stand still first). Never run against the game.
- Caveats (hypothesis): property order in memory unverified (Engine_plain.u is binary; name table order only); the Location copy found may be in a different object (Controller/replication copy), so several unrelated hits are possible; if the position unit is not 1:1 with memory the scale patterns may miss. Win64 struct layouts differ from the Win32 +0x298 guess, hence the window scan.

## Cheat Engine fallback (if the tool finds nothing)
1. Attach to Kingdom-Win64-Shipping.exe while hero stands after a jump. Value type Float, scan "exact" for the hero y from the log (e.g. 4.1708; use x or z if y is not distinctive), or "Unknown/changed" tricks: scan, jump, scan changed, stand, unchanged.
2. Right-click hit -> Browse this memory region; look +-0x300 bytes (view as Float) for the run `GroundSpeed WaterSpeed AirSpeed LadderSpeed AccelRate JumpZ` ending with JumpZ=600 (or 420 default).
3. Alternative: search exact float 600 then 2048 in "Float" and check for neighbours; or search 4 bytes "JumpZ=600" with many hits -> filter by neighbouring 5 floats.
4. If GroundSpeed/AccelRate = 0: double-click value, set 450 / 2048, freeze, press W. If W then walks, root cause confirmed: find the native writer (hero spawn path 0xe19260 / 0xdf26b0 and SoldierInfo-derived InitWithPawnInfo values).
