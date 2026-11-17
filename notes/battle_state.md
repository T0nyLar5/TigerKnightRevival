# Battle server: current state (2026-11-08; working base = V37)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Deep detail: notes\battle\ and notes\re\ (map in notes\INDEX.md). Old walk variants V17-V36 and their dead ends: reports/20261107_0230_battle_state_archive_8b_10.md.
Addresses: `10xxxxxx` = SyncClient.dll / Sync.dll (Win32); `00xxxxxx` = Kingdom-Win32-Shipping.exe; `exe+0x...` / `0x14xxxxxxx` = Kingdom-Win64-Shipping.exe (image base 0x140000000).


## 1. Status
- **V37 = WORKING BASE** (verified in game): V30 + hero DataSet float slots [0x26],[0x27] = 1.0 (raw f32; same slots in the ReBorn DataSet). The hero walks.
- **Walking works for the whole battle with `走路輔助.bat`** (`tools\ue_inspect.py --walkhelper`, admin auto). Start it after the hero appears. It writes the hero Location into the sync object exe+0x195F340 at +0x14/+0x20.
- Works: lobby `gameStartup` launches Kingdom-Win64-Shipping.exe with `-bTCP` (client newudp=0); TCP connect; MsgConnect + ConnectAck; map loads; LoadingComplete; empty frames every 50 ms; ping 0x279c needs no reply; hero spawns.
- Best before V37: V18/19 (jump, attack, block OK; no ground walk).
- **Open issues:**
  - Sprint: double-W makes the client send 0x273e (uid) / 0x2778; no server reply yet.
  - NPC/object interactions react abnormally.
  - Pull-back: the native snap-back still teleports the hero ~10 m back to (0.5,-0.6). The walk helper masks it. **Permanent fix candidate:** call `KingdomPawn.ForceUpdatePlayerHumanLocation` through the .u patch pipeline (native exec thunk 0x140a51a50, vtable+0xaf8). Not built yet; no server-side entry.
  - V29 troops + AI + battle end: untested (walking now works, so test it next).
  - Results screen: unverified (section 5).
  - Duplicate hero (0x4e22 vs slave AddPlayer vs ReBorn, V11/V12): unresolved, low priority.
- **NEVER send CmdSync (0x4e20):** stuck loading.

## 2. Topic notes (the old sections 2-7 moved here, unchanged)
- Wire format, frame stream cipher, message tables (old sections 2-3): `battle/wire_and_messages.md`
- DataSet slot meanings (section 4): `battle/dataset_slots.md`
- Countdown, BattleStart/End, results, config and key functions (sections 5-6): `battle/countdown_results.md`
- Walking, speed factor and snap-back (section 7): `battle/walk_snapback.md`
- Old walk variants V17-V36: `reports/20261107_0230_battle_state_archive_8b_10.md`

## 3. Key facts (short)
- Snap-back: teleport = FUN_140ae0370 copies hero sync object obj+0x14 to obj+0x20 (exe base 0x140000000; global DAT_14195f340). Walk helper keeps both fields = hero Location. Permanent fix not built.
- Walk helper: `走路輔助.bat` (`tools\ue_inspect.py --walkhelper`), start after hero appears.
