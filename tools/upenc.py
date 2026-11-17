#!/usr/bin/env python3
"""Re-encode a patched plain UE3 package back into the game's TK01 format (inverse of updec.py `plain`).
Method (patch splice): the header/summary and every chunk whose plain bytes equal the BASE plain file keep the original
encrypted bytes untouched, so encoding an unpatched plain file reproduces the original file byte-for-byte.
Only differing chunks are re-compressed (own LZO1X encoder below: valid stream, ratio worse than LZO999), split in
128 KB blocks, each block XORed from byte 0x2a with the TK01 keystream; the plaintext chunk table (offset 0x75) is rewritten.
usage: upenc.py encode ORIG_TK01 BASE_PLAIN NEW_PLAIN OUT_TK01
       upenc.py selftest"""
import sys, os, struct, mmap
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import updec, lzo1x

BS = 131072
TAG = 0x9e2a83c1

def lzo1x_compress(src):
    """Greedy LZO1X encoder: literal runs + M3 matches (dist<=0x4000) + end marker 11 00 00. Valid for any standard decoder."""
    src = bytes(src); n = len(src); out = bytearray(); tbl = {}
    after_match = False        # last token was a match (its 2 low bits of the distance word hold 0..3 trailing literals)
    def lit_run(a, b):
        L = b - a
        if L <= 18: out.append(L - 3)
        else:
            e = L - 3 - 15; z = (e - 1)//255
            out.append(0); out.extend(b'\0'*z); out.append(e - 255*z)
        out.extend(src[a:b])
    def flush(a, b):
        L = b - a
        if L == 0: return
        if not out:                                     # stream start
            if L <= 238: out.append(L + 17); out.extend(src[a:b])
            else: lit_run(a, b)
        elif L <= 3: out[-2] |= L; out.extend(src[a:b]) # only ever called right after a match
        else: lit_run(a, b)
    def match(dist, ln):
        l2 = ln - 2
        if l2 <= 31: out.append(32 | l2)
        else:
            e = l2 - 31; z = (e - 1)//255
            out.append(32); out.extend(b'\0'*z); out.append(e - 255*z)
        d = (dist - 1) << 2
        out.append(d & 255); out.append(d >> 8)
    pending = 0; i = 0; end = n - 4
    while i < end:
        key = src[i:i+4]; c = tbl.get(key); tbl[key] = i
        if c is not None and i - c <= 0x4000:
            ln = 4; mx = n - i
            while ln + 8 <= mx and src[c+ln:c+ln+8] == src[i+ln:i+ln+8]: ln += 8
            while ln < mx and src[c+ln] == src[i+ln]: ln += 1
            flush(pending, i); match(i - c, ln)
            for j in range(i + 1, min(i + ln, end), 1 if ln < 64 else max(1, ln // 16)): tbl[src[j:j+4]] = j
            i += ln; pending = i
        else:
            i += 1
    flush(pending, n)
    out.extend(b'\x11\x00\x00')
    return bytes(out)

def encode_chunk(plain, c):
    """plain: bytes of the chunk (len c[1]) -> chunk blob (header + block table + xored LZO blocks)"""
    blocks = []
    for p in range(0, len(plain), BS):
        u = plain[p:p+BS]; z = lzo1x_compress(u)
        assert lzo1x.decompress(z) == u, 'LZO self-check failed'
        blocks.append((updec.unxor_block(z), len(u)))   # xor is its own inverse
    hdr = struct.pack('<4I', TAG, BS, sum(len(b) for b, _ in blocks), len(plain))
    tbl = b''.join(struct.pack('<2I', len(b), u) for b, u in blocks)
    return hdr + tbl + b''.join(b for b, _ in blocks)

def inplace_chunk(d, c, old, new, log=print):
    """Patch differing bytes directly inside the original LZO streams when every differing byte is a LITERAL byte of the stream
    (token walk via lzotok). Keeps all compressed sizes identical. Returns the new chunk blob, or None if some byte is inside a match."""
    import bisect, lzotok
    tag, bs, cs, us = struct.unpack('<4I', d[c[2]:c[2]+16]); nb = (us + bs - 1)//bs
    bl = struct.unpack('<%dI' % (2*nb), d[c[2]+16:c[2]+16+8*nb])
    blob = bytearray(d[c[2]:c[2]+c[3]]); base = 16 + 8*nb
    diffs = [i for i in range(len(old)) if old[i] != new[i]]
    byblk = {}
    for p in diffs: byblk.setdefault(p // bs, []).append(p)
    for bi, ps in byblk.items():
        start = base + sum(bl[2*k] for k in range(bi))
        toks = lzotok.tokens(updec.unxor_block(bytes(blob[start:start+bl[2*bi]])))
        starts = [t[3] for t in toks]
        for p in ps:
            r = p % bs; t = toks[bisect.bisect_right(starts, r) - 1]
            if t[0] != 'L' or not (t[3] <= r < t[4]):
                log('  byte %#x (block %d rel %d) is inside a %s token: in-place impossible' % (p, bi, r, t[0])); return None
            blob[start + t[5] + (r - t[3])] ^= old[p] ^ new[p]
    log('  in-place literal patch of %d byte(s), chunk size unchanged' % len(diffs))
    return bytes(blob)

def encode(orig_path, base_path, new_path, out_path, log=print, inplace=True, force=()):
    d = open(orig_path, 'rb').read(); ch = updec.chunks(d)
    fb = open(base_path, 'rb'); fn = open(new_path, 'rb')
    mb = mmap.mmap(fb.fileno(), 0, access=mmap.ACCESS_READ); mn = mmap.mmap(fn.fileno(), 0, access=mmap.ACCESS_READ)
    assert len(mb) == len(mn), 'plain size differs (same-length patches only)'
    assert mb[:ch[0][0]] == mn[:ch[0][0]], 'plain header differs; header re-encode not supported'
    blobs = []; changed = []
    for i, c in enumerate(ch):
        same = mb[c[0]:c[0]+c[1]] == mn[c[0]:c[0]+c[1]]
        if same and i not in force:
            blobs.append(d[c[2]:c[2]+c[3]]); continue
        blob = inplace_chunk(d, c, mb[c[0]:c[0]+c[1]], mn[c[0]:c[0]+c[1]], log) if (inplace and not same) else None
        if blob is None:
            log('re-encoding chunk %d (plain %#x..%#x)' % (i, c[0], c[0]+c[1]))
            blob = encode_chunk(mn[c[0]:c[0]+c[1]], c)
        blobs.append(blob); changed.append(i)
    first = ch[0][2]; tbl_end = 0x75 + 16*len(ch)
    table = bytearray(); off = first
    for c, b in zip(ch, blobs):
        table += struct.pack('<4I', c[0], c[1], off, len(b)); off += len(b)
    out = bytearray(d[:0x75]) + table + d[tbl_end:first] + b''.join(blobs)
    open(out_path, 'wb').write(out)
    # verify changed chunks decode back to the new plain bytes
    d2 = bytes(out); ch2 = updec.chunks(d2)
    for i in changed:
        assert updec.read_chunk(d2, ch2[i]) == mn[ch[i][0]:ch[i][0]+ch[i][1]], 'verify failed chunk %d' % i
    log('wrote %s (%d bytes, orig %d), changed chunks %s' % (out_path, len(out), len(d), changed))
    return changed

if __name__ == '__main__':
    if sys.argv[1] == 'encode': encode(*sys.argv[2:6])  # (patched build options: see upatch.py)
    elif sys.argv[1] == 'selftest':
        import random
        random.seed(1)
        cases = [b'', b'a', b'abc', b'abcd'*3, bytes(random.randrange(256) for _ in range(5000)), b'\0'*100000,
                 bytes(random.choice(b'abcdefgh') for _ in range(70000)), (b'hello world '*50 + bytes(range(256))*3)*40]
        for s in cases:
            z = lzo1x_compress(s); assert lzo1x.decompress(z) == s, len(s); print(len(s), '->', len(z), 'ok')
