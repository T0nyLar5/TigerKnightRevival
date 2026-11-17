# Lobby protocol: login flow and first screens (table of contents)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary: Pomelo lobby login flow, from the auth and entry routes through the data loading, the 23-step init chain (3b) and the push routes.
Source: notes/lobby_protocol.md lines 1-98 (sections up to 4) (text moved unchanged, split 2026-11-06). Sources and tags are in the first part.

## Parts
- [login_flow_auth_entry.md](login_flow_auth_entry.md): sources and tags, KEY FACT (success is `code: 0`), transport, section 1 (connector.entryHandler.auth), section 2 (entry).
- [login_flow_data_loading.md](login_flow_data_loading.md): section 3 (data loading after entry, response shapes per route).
- [login_flow_init_and_push.md](login_flow_init_and_push.md): section 3b (23-step init chain, why the loading screen stalls) and section 4 (push routes).
