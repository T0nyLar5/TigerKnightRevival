# Script packages (*.u) - format and decryption
> rev 1 | 2026-11-08 01:40 | baseline stamp after notes reorg (2186f53)

Files: `KingdomGame\CookedPC\KingdomGame.u` (156 MB), Engine.u, GameFramework.u. Tool: `tools\updec.py` (+ `tools\lzo1x.py`, pure-python LZO). Output goes to `tools\work\` (gitignored; never commit decrypted game files).

## Format (UE3 version 0x361 = 865, cooker 0x88)
- Magic "TK01" replaces C1 83 2A 9E. The loader is Kingdom exe `FUN_0048d8e0` (summary), xor routine `FUN_004990c0` (VA 0x4990c0).
- Cipher = the same 761-byte table as the .bin configs (`tools\uecfg_key.bin`). **Every Serialize() call is XORed separately**: for a field of n bytes, k=(n*0x3b98d+0x3aa29)&0xffffffff, byte j ^= KEY[k%761], k=k%761+1. The keystream restarts per field and depends only on the field length. So there is NO whole-file keystream; cfgdec/tkcrypt/uecfg-whole-file do not work.
- Summary fields (ver, headersize, FString folder "None", flags 0x62a80008, name/export/import counts+offsets, GUID, generations, versions, compression flags) are per-field XORed. Counts: 20112 names, 59277 exports, 1797 imports.
- Compression flags = 2 (LZO). The chunk table (212 chunks, 16 bytes each at file offset 0x71: uncOff, uncSize, compOff, compSize) is **plaintext**. Chunk 0 = the 4.9 MB header area (name table at uncompressed 0x24a9, imports, exports, depends); other chunks = export data.
- Chunk = standard UE3 header (C1832A9E, blocksize 0x20000, compSize, uncSize, then (comp,unc) pairs) + blocks. Each compressed block: bytes [0x2a:] are XORed with the same table (n=len-0x2a, `FUN_004990c0(buf,len,0x2a)`), then LZO1X. Decompressed data is plain (names confirmed readable).

## Usage
`tools\.venv\Scripts\python.exe -I tools\updec.py names <KingdomGame.u> tools\work\KingdomGame_names.txt`
Functions `chunks()`, `read_chunk()` in updec.py decompress any chunk. A full rebuilt package (summary fields re-encoded plain, chunks laid out at uncompressed offsets, flags cleared) is NOT written yet; exports/bytecode are not parsed.

## Movement-gate candidate names (KingdomGame.u, 20112 names)
IgnoreMoveInput, bIgnoreMoveInput, IsMoveInputIgnored, IgnoreLookInput, ResetPlayerMovementInput, bLockSpeed, bMovable, bMoveableOnNoForce, SetMoveableBeforeEquipingAmmoTimer, bCanMoveOnEquippingAmmo, fLastComboHitCanMoveTime, PlayerWalking, PlayerMove, ProcessMove, CallServerMove, NetMoveDelta, HandleWalking, MaxWalkingSpeed, AdjustPlayerWalkingMoveAccel, fPlayerMoveStrafeSpeedFactor, SyncReqMoveStyleChange.
Battle-start gating: bWaitingToStartMatch, ReadyToStartMatch, StartMatch, PreStartMatch, MatchStarting, NotifyMatchStarted, IsGameStartedForClient, IsBattleStarted, IsInBattleState, CheckCurrentBattleStateIsFighting, Event_OnStartFight, SyncReqGameStart, OnGameStart, BattleStart, iBattleStart, fBattleStartSecond, bShowGameStartCountDown, bStopCountDown, DrawGameStartCountDown, ShowGameStartTimeout, ShowBattleStartEffect, CountDownTime, BlockGameStart.
Strongest suspects: bIgnoreMoveInput / IsMoveInputIgnored (set until countdown/battle start) and IsGameStartedForClient / IsBattleStarted / SyncReqGameStart (server must tell the client the game started).

## UE Explorer / decompiler
Not tried (no downloads). It reads standard UE3 packages, so it needs the package rewritten as a plain, uncompressed file (summary re-encoded, chunks unpacked, compression flags 0, tag C1832A9E); UE Explorer also needs a matching UE3 version (865 is within its supported range, but Tiger Knight is a modified engine, so success is uncertain). That rebuild is the next step if the user consents to the download. Alternative without a decompiler: parse the export table and read raw bytecode of the candidate functions.
