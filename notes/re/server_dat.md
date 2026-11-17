# Server.dat / langandplatform.dat decryption
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

## Result: SOLVED (both files). Round-trip enc(dec(Server.dat)) is byte-identical to the original.

## Cipher (frontend.exe, class with vtable 0xd3ad94; decode routine at VA 0xa45790, key init 0xa451a0)
- Key table: `srand(0x2537)`; `key[i] = rand() & 0xff` for i in 0..127 (MSVC LCG: s = s*214013+2531011; rand=(s>>16)&0x7fff).
- Decrypt byte i:  `t = c ^ key[i % 128]`;  `p = rotr8(t, i % 8)`
- Encrypt byte i:  `c = rotl8(p, i % 8) ^ key[i % 128]`
- No header, no padding, length preserved (file is plain text after decrypt; Server.dat starts with a UTF-8 BOM).
- Tool: `tools/tkcrypt.py dec|enc in out`. Decrypted: `notes/decrypted/Server.dat.txt`, `langandplatform.dat.txt`.

## How found
Disassembled frontend.exe (capstone, venv in `tools/.venv`, helpers `tools/xref.py`, `tools/disasm.py`, `tools/consts.py`). String "server.dat" -> INI loader (0x96ca20: `Load(name, flag)`; flag 1 = encrypted) -> vtable Open/ReadLine at 0xa45a90/0xa45b00 -> decode 0xa45790.
Note: the loader for `langandplatform` first tries plaintext `langandplatform.ini` (flag 0), then falls back to `.dat` (flag 1). So a plain `langandplatform.ini` next to the exe overrides the .dat.

## Server.dat contents (INI), single district
```
[JieQiao(Asia)]
DistrictName=国际服#International#國際服
RandServer=1
ServerId=29
AreaID=1
ServerAmount=10
ServerName{N}={N}              N=1..10
ServerUP{N}=front1-hk.tk.99.com
ServerIP{N}=front1-hk.tk.99.com
ServerPort{N}=3009+N           (3010..3019)
ServerUP{N}_PING=back1-hk.tk.99.com
ServerIP{N}_PING=back2-hk.tk.99.com
ServerPort{N}_PING=10425       (all)
```
Full text in `notes/decrypted/Server.dat.txt` (86 lines).

## Hosts / ports
- Lobby/gate (Pomelo): **front1-hk.tk.99.com**, ports **3010-3019** (one per "server" 1..10). Log showed `serverid:3` was picked -> likely port **3012** (ServerPort3), unconfirmed; RandServer=1 so the client chooses randomly. Listen on all of 3010-3019 to be safe.
- Ping servers: back1-hk.tk.99.com / back2-hk.tk.99.com port 10425 (only used when `[OPEN_PING_SERVER] open=1`; langandplatform currently has open=0).
- Hosts file redirect of front1-hk.tk.99.com -> 127.0.0.1 is sufficient; no need to re-encrypt. (To re-encrypt anyway: edit the .txt, keep the BOM, `python tools/tkcrypt.py enc ... Server.dat`.)
- Other URLs in frontend.exe (not login): http://hbqtv.99.com/ , http://pay.ixinyou.com/payment-web/main/product?... , http://zhifu.99.com/WFTPay/Scan/GamePoaForHBQ.aspx , http://collect.mdata.cool/mdata.php?sign= (telemetry), <OFFICIAL_IP>:55003 and <LAN_IP>:55003 (mdata). No auth/patch HTTP URL found in static strings (may be in Lua/other data).

## langandplatform.dat (decrypted)
```
[LANG] language=2
[PLATFORM] platform=1
[UNREAL] u3=0
[LPLOG] Level=3
[RECONN_RETRY] Retry=0
[SSL] EnableSSL=1
[OPEN_PING_SERVER] open=0
[NOPRELOADCACHE] open=0
```
**EnableSSL=1**: the Pomelo connection is probably TLS-wrapped. Log shows `pCaPath:` in connect events. A local server may need TLS (self-signed cert + client CA handling) OR set EnableSSL=0 via a plaintext `frontend\bin\langandplatform.ini` (same section/keys) -- untested.

## Transport
PoClientDLL.dll is libpomelo2 with only the `tr_uv_tcp` transport (strings `tr_uv_tcp_*`, `tcp__*`; no websocket strings). So it is **raw TCP** (libuv) with Pomelo handshake/heartbeat framing, optionally TLS (OpenSSL linked, EnableSSL). g_bUseTCP:0 is a game-level flag (Lua_SetUseTCP), not the Pomelo transport. Routes seen in PoClientDLL: connector.entryHandler.{auth,entry,heartbeat,queryServerTime,test}, chatconnector.chatHandler.{entry,channelChat}. Handshake is JSON in Pomelo package format (type 1), serializer/ dict from handshake response.

## Unresolved
- `Silent.dat`, `*.bin` (UE ini), both `config.cfg`: NOT the same cipher (decrypt with this key gives binary). Probably handled by Platform.dll / the UE3 binary (KingdomGame) with a different scheme. Not needed for login.
- Confirm TLS requirement / CA handling at runtime (look at pCaPath logic in PoClientDLL, tr_uv_tcp_connect).
