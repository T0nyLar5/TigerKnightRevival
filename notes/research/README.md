# Research guide (static analysis and background)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

This folder holds research notes, mostly static analysis (Ghidra, RTTI, byte scans) of the battle DLLs and exe, plus background from web and Wayback Machine searches. Findings are hypotheses until a real battle test confirms them. Current battle state is in `..\battle_state.md`.

Which file to read for which question:
- `research_input.md`: table of contents. Read it to find the part you need.
- `research_input_client_messages.md`: read when working on which client-to-server Req messages exist (types 0x2717..0x27c3).
- `research_input_relay_and_battle_start.md`: read for the relay rules that `server\battle_server.py` should follow, and for battle start and end (slave messages 8 and 9).
- `research_input_battle_end_unknowns.md`: read for how a battle ends, what the lobby receives, and the open unknowns with test hints.
- `research_troops.md`: table of contents for troops. Read section 0 corrections first.
- `research_troops_creation.md`: read when creating a soldier Ctl (message 0x4e23) and its DataSet slots.
- `research_troops_slave_addperson.md`: read when writing the slave AddPerson (msg 3) for soldiers.
- `research_troops_plan.md`: read for the proposed minimum squad sequence (its a=3 values are superseded).
- `research_troops_unknowns_update.md`: read for the open unknowns, the function index, and the 2026-11-05 PM update (agentType a=1).
- `research_ai.md`: read when working on enemy AI (the `ai::` namespace in SyncClient.dll).
- `web_research.md`, `wayback_research.md`: read before repeating web or Wayback searches (background only; no private-server or protocol write-up was found).

Status: the research notes from 2026-11-05 cover the listed topics; none is verified in a live battle test yet.
