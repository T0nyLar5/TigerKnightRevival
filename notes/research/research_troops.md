# Research: troops (player squads, 小兵) -- static analysis, 2026-11-05 (table of contents)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Method: Ghidra headless on Win32 Sync.dll, SyncClient.dll, Kingdom-Win32-Shipping.exe (private project `ghidra_projects_a`), 34 function decompiles + free pefile/capstone scans. Addresses: `10xxxxxx` = SyncClient.dll or Sync.dll (stated per item), `00xxxxxx` = Kingdom exe. Conf: H = read directly, M = layout read / meaning inferred, L = guess.

## 0. Corrections to earlier notes (IMPORTANT)
- **Slave msg 2 is AddCreature, slave msg 3 is AddPerson** (not the other way round). Sync.dll dispatcher `0x10034630`: type 2 -> `0x10033d40` -> `0x10038620` (RTTI cast to `ICreatureEvent`, allocates `CreatureSlave`); type 3 -> `0x10033e40` -> `0x10038810` (`IPersonEvent`, `PersonSlave`); type 4 -> `0x10038a00` (`IBulletEvent`, `BulletSlave`: it is **AddBullet**, not a unit). [H] `server/battle_proto.py` (line 41) labels 2 = SlaveAddPerson, 3 = SlaveAddCreature; this is swapped.
- Soldiers are **Persons** (SyncClient class `syncclient::SoldierCtl` = `PersonCtl<IPersonCtl, IPersonEvent, ISoldierMir>`), so a troop uses slave **msg 3**. Horses are Creatures (msg 2). [H]
- The slave unit messages are only half of the story. Like the hero, a troop needs a **top-level SyncClient message that creates the control object (Ctl) and its DataSet first**: `MsgCmdAddCreature` (0x4e23).

## Parts
- [research_troops_creation.md](research_troops_creation.md): section 1 (top-level 0x4e23 creates the Ctl) and section 2 (DataSet slots for a soldier).
- [research_troops_slave_addperson.md](research_troops_slave_addperson.md): section 3 (slave AddPerson msg 3 wire layout).
- [research_troops_plan.md](research_troops_plan.md): sections 4-6 (other candidate messages, config ids, proposed minimum sequence).
- [research_troops_unknowns_update.md](research_troops_unknowns_update.md): section 7 (unknowns), section 8 (function index), UPDATE 2026-11-05 PM (agentType correction).
