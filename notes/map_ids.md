# Map ids (mapId in gameStartup -> `?map=` and map name on UE3 command line)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Source: mapindex.txt itself is still inside encrypted `frontend/bin/config.cfg` (not decoded). The ids below come from
plain-text tables that use the same ids:
- `frontend/bin/data/ani/map.ani` (GBK text, `[id]` -> minimap image, comment = Chinese map name) [C for id -> theme]
- `KingdomGame/Config` `DefaultGame.ini` `[Loading] MapBackground<id>` and `.MapTables=(MapNameWildcard=..,MapID=..)` (notes/decrypted/ue_config)
Consistency check: UE MapTables 1 SyncTest, 2 walktest, 3 bowangpo, 4 chibi, 5 weinan matches map.ani/Loading ids 3/4/5 and the observed error "map 'SyncTest'" for mapId 1. So mapId 1 = SyncTest (no such map shipped), 2 = walktest.

| id | theme (map.ani / Loading) | candidate umap in CookedPC\Maps | note |
|---|---|---|---|
| 1 | SyncTest | none | NOT usable |
| 3 | 博望坡 bowangpo | TA_Bowangpo_hdr | |
| 4 | 赤壁 chibi | ChiBi\TA_ChiBiTest_001 | |
| 5 | 渭南 weinan | WeiNan\TA_weinan_20 | |
| 6 | 官渡 guandu | GuanDu | |
| 7 | 雪原 snowPK | XueDiPK | |
| 8 | 樊城 fancheng | FanChen | |
| 10 | 界橋 jieqiao | JieQiao | |
| 11 | 新手 xinshou (tutorial) | TA_XinShouJiaoXue_133_MH | gameMode 1 |
| 12 | 討伐教學 taofajiaoxue | TaoFaZhanTutorial\TA_TaoFaZhanTutorial_001 | gameMode 4 |
| 13 | 定軍山 | DingJunShan / PVP_GJ_Dingjunshan | |
| 15 | 車輪戰 / 博望校場 | ? | |
| 16 | 洛陽皇宮 | ? | |
| 17 | 訓練場 XunLianChang | PK_CL_Yanwuchang / PK_YanWuChang (演武場) | gameMode 5 challenge training (best guess) |
| 18 | 虎牢關 | ? | |
| 19 | 陽人之戰 | PK_YangRenZhiZhan | |
| 20 | 漢宮巷道 | ? | |
| 21 | 建業校場 | ? | |
| 22 | 南中之亂 | NanMan | |
| 23 | 下邳 | XiaPi | |
| 24 | 水鄉烽煙 | ? | |
| 25 | 雲夢澤 | ? | |
| 27 | 涼州荒村 | ? | |
| 28 | 江表大宅 | ? | |
| 29 | 角鬥場 | ? | |
| 30 | 塞外烽火 | ? | |
| 32 | 蠻荒前哨 | ? | |
| 33 | 阿萊西亞 | Alaixiya | |
| 34 | 雪原(聖誕) | | |
| 35 | 高盧郊野 | GaoLuJiaoYe | |
| 36 | 荒漠綠洲 | Beifeishamo | |
| 37 | 黑森林 | HeiSenLin | |
| 38 | 泰拉蒙 | Yidalijiaoye | |
| 39 | 羅馬軍營 | LuoMaYaoSai | |
| 42/43/44/46/47 | 領土戰中原 / 隴西 / 百將戰 / 酒泉 / 博望校場(聖誕) | ? | |
| 99 | 虎牢關+火燒洛陽 | | |

Confidence: ids -> themes high; theme -> exact umap file medium (the final name string is only in config.cfg). gameMode 1 -> 11 and 4 -> 12 are high (loading screen names match tutorial classes); gameMode 5 -> 17 is medium (only "training ground" map in the list; which of the two Yanwuchang umaps is unknown, UE picks it by name from mapindex anyway). PvE epic (gameMode 6) id left unset. If the battle exe again reports a missing map, the message shows the name the frontend chose, which pins the table.

## UPDATE 2026-11-05 PM
mapindex.txt is decrypted (notes/decrypted/cfg/sync_config/config/mapindex.txt). Authoritative: 11 TA_XinShouJiaoXue_133_MH, 12 TA_TaoFaZhanTutorial_001, 17 PK_CL_Yanwuchang_005 (骑射演练场), 21 PK_Yanwuchang_00 (建业校场). Map 17 has no camp positions.
