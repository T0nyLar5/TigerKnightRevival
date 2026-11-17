# Battle sync: step 1 results and SyncClient wire format (section 8)
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)
Part of [sync_protocol.md](sync_protocol.md) (table of contents).

## 8. Step 1 results (battle phone-listener; static analysis of Win32 SyncClient.dll)
Direct launch (bat `5_直接開啟戰鬥程式.bat`, cwd = `Binaries\Win64`, Win32 fallback):
`Kingdom-Win64-Shipping.exe TA_XinShouJiaoXue_133_MH?game=kingdomgame.KingdomTutorialSyncGame?ip=127.0.0.1?port=7777?id=10001?map=1?ResX=1920?ResY=1080?Token=12345 -LANGUAGE=CHT -WINDOWED -novsync -bTCP`
Unsure: map name (tutorial map files are `TA_XinShouJiaoXue_*.umap` in CookedPC\Maps; `_133_MH` is a guess for the main level; mapindex.txt not decoded), `map=1`, ParentWnd omitted (0 or absent may crash/exit), the `?` option syntax assumes the stock UE3 URL form, `-dx9/-dx11` omitted.

SyncClient wire format (TcpConnector; Connect at 0x100d7e90 `(ip,port,a,b,c)`, MsgConnect built at 0x100d8960..0x100d8a09, serializer 0x10049d30, cipher 0x100db3f0 / init 0x100da1c0):
- Frame (plaintext): `u16 len (counts itself) | u16 type | body`, little endian. len is back-patched after writing body.
- Whole TCP stream is XORed with a fixed keystream (no key exchange, counter starts at 0 per connection and per direction, continues across frames): `ks[n] = A[n%256] ^ B[(n//256)%256]`; A: x=0x1f; A[i]=x; x=((((x<<5)&0xff)+0xfd)*x+7)&0xff. B: c=0x3f; B[i]=c; t=(((c*0x7a)-0x31)*c)&0xff; c=(t-0x1b)&0xff. Implemented in `server/battle_probe.py` (`crypt`). Confidence: high on algorithm reading, but untested against real traffic.
- MsgConnect: type 0x3e9, len 20: `u32 1 | u32 a | u32 b | u32 c` where a,b,c are the Connect args (a = id, b = 1, c = token/X, per Create's arg order from section 3; medium confidence on which is which).
- MsgConnectAck: not located with certainty. Types seen: 0x3ea is an 8-byte header-only object the client enqueues locally right after sending MsgConnect and dispatches as "connected" (0x100ae061 -> callback vtable+0x264); 0x3eb is handled in 0x100b0e70 (maybe ping/ack); 0x2711/0x2712/0x2715/0x2716/0x3f3 handled in dispatcher 0x100ae390/0x100ade96. Guess: server ack = frame `04 00 ea 03` or a 0x3eb frame (both XORed). Low confidence. Next: read the probe log, then decode 0x100b0e70.
- UDP/KCP path not analysed.
