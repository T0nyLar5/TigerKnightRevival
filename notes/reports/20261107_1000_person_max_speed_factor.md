# fPersonToSelf/HorseMaxSpeedFactor = 0 : source found (2026-11-07 10:00)

## Live fact (verified, key F)
KingdomChallengePlayerController_0: fPersonToHorseMaxSpeedFactor (+0x7A4) and fPersonToSelfMaxSpeedFactor (+0x7A8) read 0.00. Class default is 1.0 (tools\work\cls\KingdomPlayerController.class.txt:252-254, 6462-6463). No script function references them.

## Source of the 0 (static, likely - NOT yet verified in game)
Native writer found by scanning Kingdom-Win64-Shipping.exe for [reg+0x7A4]/[reg+0x7A8] stores:
- Function 0x140aed840 (huge, ~0x1f0+ bytes of prologue/readers), writes at **0x140aee73f** (+0x7A4) and **0x140aee765** (+0x7A8).
- r13 = (global [0x141...rip+0xe71a6c])->vtable[+0x28]() ; then vtable[+8](r13, idx) reads ints at idx 2 (health), 3, 0x4b (Energy) ... = the local player's **DataSet** accessor (same slots as notes\battle_state.md section 4). vtable[+0x18](r13, idx) = float getter.
- +0x7A4 = max(DataSet float[0x27], 1e-4) ; +0x7A8 = max(DataSet float[0x26], 1e-4). Floor constant at 0x1411a0fd4... = 9.99999747e-05 (so 0.00 on screen = 0.0001).
- Our server never sets DataSet slots 0x26 / 0x27 (all zero) -> both factors become 0.0001 -> MaxSpeed ~ 0 -> hero creeps ~0.05 UU/s while holding W. Fits every symptom (no walk anim: BlendBySpeed Speed=0; jump still works).
- Not from ini/cfg: grep of notes\decrypted\ue_config and cfg tables finds no PersonToSelf/PersonToHorse (only formation.txt fMaxSpeedFactor, unrelated per-formation column). var(Param) fields are not loaded from a config file here.
Confidence: likely (static; slot meaning 0x26/0x27 as f32 is inferred from the comiss/max code, not seen with a real server).

## What was added
- tools\ue_inspect.py `--factor` / 英雄速度檢查.bat key **G**: reads both fields, then 1 = write 1.0 every ~10 ms for 10 s while W is held (prints Location, restores), 2 = write once and leave, 3 = write any Float/Int field of the CONTROLLER by name (y to confirm). Needs admin for writes. Selftest (offline) OK.
- server\battle_server.py **variant 37** (untested): V30 + DataSet[0x26]=[0x27]=f32 1.0. Run via 一鍵測試_選版本.bat with 37.

## Test order for the user
1. Key G, sub-mode 2 (write once), then walk freely. If the hero walks: confirmed, next test variant 37 so no memory write is needed.
2. If it does not walk after key G: the factors are not the (only) gate; keep V37 low priority.
