# Wayback Machine research: Tiger Knight (虎豹骑) / NetDragon 99.com
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Method: Wayback CDX API (`web.archive.org/cdx/search/cdx`, JSON, `collapse=urlkey`, `limit=2000`). No binaries were downloaded; only CDX listings were read. Size is the CDX `length` field in bytes. Links are `http://web.archive.org/web/<timestamp>/<url>`.

## Summary table

| Domain | Captures (unique URLs) | Notes |
|---|---|---|
| hbq.99.com | ~388 | Complete (below the 2000 limit). Only the first ~120 interesting rows were reviewed. |
| tk.99.com | ~258 | Complete (below the 2000 limit). |
| zy.down.99.com/gw/hbj/ | 0 | Zero captures |
| hbj.99.com | 0 | Zero captures |
| tigerknight.99.com | 0 | Zero captures |
| tigerknight.com | 0 | Zero captures |
| www.tigerknight.com | 0 | Zero captures |
| front1-hk.tk.99.com | 0 | Zero captures |

The zero-capture domains returned an empty CDX result. They were not checked separately for errors.

## hbq.99.com (interesting URLs)

- http://hbq.99.com:80/download/uninstall.shtml, 20170424034125, 5054 bytes, 200
  http://web.archive.org/web/20170424034125/http://hbq.99.com:80/download/uninstall.shtml
- http://hbq.99.com/download/?cbigame, 20150204080149, 4536 bytes, 200
  http://web.archive.org/web/20150204080149/http://hbq.99.com/download/?cbigame
- http://hbq.99.com:80/feiye/cfg_v1/, 20150822202203, 293 bytes, 403 (a `cfg_v1` directory exists but is forbidden)
  http://web.archive.org/web/20150822202203/http://hbq.99.com:80/feiye/cfg_v1/
- http://hbq.99.com/list/4k.rar, 20180106040012, 464 bytes, 301 (redirect record only, not a file capture)
  http://web.archive.org/web/20180106040012/http://hbq.99.com/list/4k.rar
- http://hbq.99.com/list/8k.rar, 20180106045120, 464 bytes, 301 (redirect record only)
  http://web.archive.org/web/20180106045120/http://hbq.99.com/list/8k.rar
- https://hbq.99.com/activity/2017/anchorrecruit/, 20250307173301, 3265 bytes, 200 (latest capture seen, 2025)
  http://web.archive.org/web/20250307173301/https://hbq.99.com/activity/2017/anchorrecruit/
- https://hbq.99.com/news/03212018/225407493.shtml, 20220525080308, 8451 bytes, 200 (2018 news re-captured in 2022)
  http://web.archive.org/web/20220525080308/https://hbq.99.com/news/03212018/225407493.shtml
- https://hbq.99.com/news/02112018/225123731.shtml, 20220525074003, 4490 bytes, 200
  http://web.archive.org/web/20220525074003/https://hbq.99.com/news/02112018/225123731.shtml
- https://hbq.99.com/news/01212020/224843800.shtml, 20210706084234, 4371 bytes, 200
  http://web.archive.org/web/20210706084234/https://hbq.99.com/news/01212020/224843800.shtml
- https://hbq.99.com/guide/map/, 20211207171610, 1882 bytes, 200
  http://web.archive.org/web/20211207171610/https://hbq.99.com/guide/map/
- Mobile pages: http://hbq.99.com:80/m/ (20170608041836, 1580 bytes), /m/play.shtml (20170716012940), /m/news.shtml (20170605142618)
- Guide pages: http://hbq.99.com:80/guide/faq.shtml (20170502171338, 3319 bytes), /guide/feature.shtml (20170424063540), /guide/advance.shtml (20151013024204)

Not reviewed: the remaining ~260 hbq rows beyond the first 120 filtered results. A keyword-filtered second query for hbq returned no rows, which may be a timeout or an empty filter result.

## tk.99.com (interesting URLs)

Download, install and updates:
- http://tk.99.com:80/buy/download.shtml, 20171129021723, 2722 bytes, 200
  http://web.archive.org/web/20171129021723/http://tk.99.com:80/buy/download.shtml
- http://tk.99.com:80/buy/install.shtml, 20171126180123, 2592 bytes, 200
  http://web.archive.org/web/20171126180123/http://tk.99.com:80/buy/install.shtml
- http://tk.99.com:80/news/update-announcement0-1-77.shtml, 20180128043035, 3432 bytes, 200 (version 0.1.77 patch notes)
  http://web.archive.org/web/20180128043035/http://tk.99.com:80/news/update-announcement0-1-77.shtml
- http://tk.99.com:80/news/update-announcement0-1-76.shtml, 20180128043030, 3980 bytes, 200
  http://web.archive.org/web/20180128043030/http://tk.99.com:80/news/update-announcement0-1-76.shtml
- http://tk.99.com:80/news/update-announcement0-1-75.shtml, 20180128041918, 3468 bytes, 200
  http://web.archive.org/web/20180128041918/http://tk.99.com:80/news/update-announcement0-1-75.shtml
- http://tk.99.com:80/news/update-announcement0-1-73.shtml, 20180128043025, 9322 bytes, 200
  http://web.archive.org/web/20180128043025/http://tk.99.com:80/news/update-announcement0-1-73.shtml
- http://tk.99.com:80/news/update-announcement-0-1-79.shtml, 20180113235054, 6583 bytes, 200
  http://web.archive.org/web/20180113235054/http://tk.99.com:80/news/update-announcement-0-1-79.shtml
- http://tk.99.com:80/news/update/maintenance-0-0-65.shtml, 20180128042542, 3640 bytes, 200
  http://web.archive.org/web/20180128042542/http://tk.99.com:80/news/update/maintenance-0-0-65.shtml

Notices (possible shutdown or offline context; the latest captures are from 2018 to 2019, and no explicit shutdown notice was seen):
- http://tk.99.com:80/news/notice/compensation-announcement.shtml, 20180128043015, 2999 bytes, 200
  http://web.archive.org/web/20180128043015/http://tk.99.com:80/news/notice/compensation-announcement.shtml
- http://tk.99.com:80/news/notice/developers-note.shtml, 20180128043020, 3551 bytes, 200
  http://web.archive.org/web/20180128043020/http://tk.99.com:80/news/notice/developers-note.shtml
- http://tk.99.com:80/news/notice/developers-note-0324.shtml, 20180127044733, 3994 bytes, 200
  http://web.archive.org/web/20180127044733/http://tk.99.com:80/news/notice/developers-note-0324.shtml
- http://tk.99.com:80/news/notice/discord-q-and-a-announcement.shtml, 20180120062117, 2935 bytes, 200
  http://web.archive.org/web/20180120062117/http://tk.99.com:80/news/notice/discord-q-and-a-announcement.shtml
- http://tk.99.com:80/news/notice/maintenance-announcement-0323.shtml, 20180128042112, 2903 bytes, 200
  http://web.archive.org/web/20180128042112/http://tk.99.com:80/news/notice/maintenance-announcement-0323.shtml

Other: http://www.tk.99.com:80/robots.txt, 20040414014620, 1083 bytes, 404.

Not seen: any .zip, .rar, .7z, .exe, .dat, .xml, .ini, .cfg or .txt file captures, server or GM tools, API endpoints, or developer docs. The tk.99.com buy and wallet pages are commerce pages and were not reviewed further.

## Findings

- No binaries or executables were found in either domain's CDX listing.
- The closest thing to a patch list is the tk.99.com version-announcement pages (update-announcement0-x-y), dated 2018. These are text pages, not patch files.
- No server build, patch file, or protocol information was identified from the CDX listings alone. Fetching the page contents would be needed to confirm any of these.
- Shutdown or offline-play notices were not identified from URLs alone. The hbq.99.com 2021 and 2022 recaptures of 2018 news pages may be worth reading.
