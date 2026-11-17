# Tiger Knight web research (about 25 searches + 14 page fetches)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Bottom line: no public private-server, emulator, packet capture, protocol write-up or reverse-engineering project turned up in English, Simplified Chinese or Traditional Chinese. Nothing found can save work on the battle/sync server. Only background and history were found.

## Useful finds (background only)

1. Steam developer reply on player-hosted servers (appid 534500, Empire War) - relevance: medium
   https://steamcommunity.com/app/534500/discussions/0/1368380934272787403
   Moderator Pender, 30 Jun 2017: "the way the game is designed allowing players to host servers does not fit the way we have it currently". Confirms matchmaking and battle hosting were centralised, and no official dedicated-server build was released. No technical detail.

2. Steam 415660 discussion hub - relevance: medium
   https://steamcommunity.com/app/415660/discussions
   Revival requests only: "Attention Netdragon: Bring back TK" (157 comments, started 25 Nov 2022; https://steamcommunity.com/app/415660/discussions/0/3588834930886010679/), "Cant log on" (24 Sep 2025, "server dismantled forever maybe?"), "IS THERE ANYONE PLAYING THIS GAME STILL" (Jul-Aug 2025). No private-server, emulator or GitHub mentions in the threads read. Only the first ~15 comments of the long thread were visible.

3. Shutdown and relaunch history - relevance: medium (context)
   - https://www.pcgamingwiki.com/wiki/Tiger_Knight (403 on fetch; read via search snippet): game unlisted from Steam 12 Oct 2021, final update 8 Nov 2018.
   - https://mmos.com/news/tiger-knight-relaunches-day-shut and https://www.mmobomb.com/news/tiger-knight-empire-war-not-closing-will-new-server-tomorrow: Oasis Games shut down Empire War (appid 534500) on 10 Jan 2018. NetDragon relaunched it a day later as "Tiger Knight" (appid 415660, merged into one server).
   - Steam sunset notice (body text not retrievable; only the title "虎豹骑停止运营公告" came through): https://steamcommunity.com/games/TK/announcements/detail/1575563008205770890?l=schinese
   - Bilibili video (https://www.bilibili.com/video/BV1iq4y1N7QG/) and Tieba thread titled "10月9日Steam服正式停运" (https://tieba.baidu.com/p/7535804546, 403 on fetch): email received 13 Sep 2021 saying the Steam servers close permanently at 00:00 on 9 Oct 2021.
   - Only the Steam server is confirmed closed. The Tencent-published CN server and the Asia server have unconfirmed or conflicting status in the sources found.
   - No official statement about offline, private or community play was found anywhere.
   - Steam 415660 forum thread, Apr 2018: https://steamcommunity.com/app/415660/discussions/0/3288067088131725825/. Insider claims that devs were reassigned in Q4 2017 and the game was heading to maintenance mode.

4. CSDN troubleshooting article - relevance: low-medium
   https://blog.csdn.net/weixin_31764905/article/details/119406247
   - The CN client process is Kingdom-Win64-Shipping and is installed through TGP.
   - Redistributables come from http://zy.down.99.com/gw/hbj/2014/download/ and /gw/hbj/2017/download/, as hbq_1119_*.rar/zip. This may be a lead if an archived installer or patch listing is wanted.
   - No game-server hosts or ports given.
   - Internal name "hbq" (虎豹骑); the CN site is hbq.99.com.

5. CN official site and update notes - relevance: low
   http://hbq.99.com/news/12272017/20171228105424374.shtml (1.1.98 patch notes), https://games.softpedia.com/progChangelog/Tiger-Knight-Empire-War-Changelog-147592.html (client 0.1.103, 2 May 2018). Version numbers only.

6. Bahamut (Taiwan) forum - relevance: low
   https://forum.gamer.com.tw/B.php?bsn=31243 and https://forum.gamer.com.tw/Co.php?bsn=31243&sn=806 (CN server registration guide: QQ account, Tencent-published). Could hold old patch or login discussion. Not fetched.

7. Generic Pomelo docs - relevance: medium (for the lobby only)
   https://github.com/NetEase/libpomelo2 and https://github.com/NetEase/pomelo/wiki (the protocol is open and documented). Nothing Tiger Knight specific.

## Nothing found for

- GitHub: no repos or code-search hits for "Tiger Knight", tk.99.com, front1-hk, Kingdom-Win32-Shipping, KingdomGame, SyncClient.dll or ISyncMaster (the search engine ignores exact phrases, so a manual GitHub code search is still worth one try).
- "ISyncMaster", "ISyncClient" and "Sync.dll" lockstep: only unrelated Kentico and IBM results. No sign of the same middleware in other NetDragon or 99.com games.
- TQ Digital "Loong" engine (Loong.xml, `tq::`): no public material. Generic lockstep sample projects only (e.g. https://gitee.com/TYL1226/LockStepSimpleFramework-Server), which are not protocol compatible.
- Private server or emulator, in English and in Chinese (私服, 单机, 服务端, 复活, 虎豹騎 私服 單機): nothing. The only hits are unrelated games (KartRider_TW, RO single server) and "单机版" download pages (e.g. https://m.wanyx.com/game/38967.html) that look like the normal online client and should be treated as suspect.
- Packet captures and protocol write-ups: nothing on 52pojie, kanxue, CSDN or elsewhere.
- Reverse-engineering threads on ResHax, RaGEZONE, XeNTaX/ZenHAX or ModDB: nothing. ModDB has only launch news. Search engines did not index Reddit or Discord for the game.
- Internet Archive: no tk.99.com or hbq.99.com client, patch or server-file results via search. It was not checked directly. Try Wayback CDX queries for tk.99.com, hbq.99.com and zy.down.99.com/gw/hbj/*.
- Not checked: Reddit and NGA directly, and Tieba (虎豹骑吧) beyond one thread (403). Bilibili comments were not retrievable.
- Mount & Blade II mods ("骑砍2之虎豹骑重生计划", https://bbs.mountblade.com.cn/thread-2099423-1-1.html) only recreate the unit. They are not a server revival.

## Verdict
The battle server must be written from the client's own binaries (Sync.dll, SyncClient.dll, ISyncMaster/ISyncClient vtables, the packet handlers). No existing community work was found that would save effort on the battle server.
