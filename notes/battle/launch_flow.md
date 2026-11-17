# Battle launch flow: how frontend.exe starts UE3 (table of contents)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Summary: how the lobby push gameStartup makes frontend.exe launch the UE3 exe, the command line, why a direct launch fails, and the hosting verdict.
Tags: see the legend in [README.md](README.md).
Source: notes/battle_launch.md sections 1-4, 6, 7, 9 (text moved unchanged, split 2026-11-06).

## Parts
- [launch_flow_cmdline.md](launch_flow_cmdline.md): section 1 (launch flow, gameStartup) and section 2 (UE3 command line, game classes).
- [launch_flow_hosting.md](launch_flow_hosting.md): sections 3-4 (battle protocol, results, hosting verdict), 6 (unresolved), 7 (best next lead).
- [launch_flow_lobby_trigger.md](launch_flow_lobby_trigger.md): section 9 (lobby-triggered launch, the ParentWnd check, TCP option, map ids).
