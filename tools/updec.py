#!/usr/bin/env python3
"""Tiger Knight UE3 script package (*.u, magic 'TK01') reader.
Kingdom-Win32-Shipping.exe: FUN_0048d8e0 (summary serialize), FUN_004990c0 (xor), table = tools/uecfg_key.bin (761 bytes).
Scheme: every FArchive field read (one Serialize(ptr,n) call) is XORed separately with
  k=(n*0x3b98d+0x3aa29)&0xffffffff; byte j ^= KEY[k%761]; k=k%761+1
i.e. the keystream restarts per field and depends only on the field's byte length n.
Summary fields are decrypted field by field. The compression chunk table (offset 0x71) is plaintext.
Chunks: standard UE3 chunk header C1832A9E, LZO1X blocks (tools/lzo1x.py); bytes [0x2a:] of each compressed block are XORed (same KEY, n=len-0x2a).
Decompressed data (names etc.) is plain. usage: updec.py names|header PKG [names_out.txt] | plain PKG out.u"""
import sys, struct, os
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, 'uecfg_key.bin'), 'rb').read()

def xf(b):
    n = len(b); k = (n*0x3b98d + 0x3aa29) & 0xffffffff; o = bytearray(n)
    for j in range(n):
        k %= 761; o[j] = b[j] ^ KEY[k]; k += 1
    return bytes(o)

class R:
    def __init__(s, d): s.d = d; s.p = 0
    def raw(s, n): v = xf(s.d[s.p:s.p+n]); s.p += n; return v
    def i32(s): return struct.unpack('<i', s.raw(4))[0]
    def u32(s): return struct.unpack('<I', s.raw(4))[0]
    def fstr(s):
        n = s.i32()
        if n == 0: return ''
        if n > 0: return s.raw(n)[:-1].decode('latin1')
        return s.raw(-n*2)[:-2].decode('utf-16le')

def header(d):
    r = R(d); h = {}
    assert d[:4] == b'TK01'; r.p = 4
    h['ver'] = r.u32(); h['headersize'] = r.i32(); h['folder'] = r.fstr()
    h['pkgflags'] = r.u32(); h['namecount'] = r.i32(); h['nameoff'] = r.i32()
    h['exportcount'] = r.i32(); h['exportoff'] = r.i32()
    h['importcount'] = r.i32(); h['importoff'] = r.i32()
    h['_pos'] = r.p
    return h

def chunks(d):
    """compression chunk table (plain, right after compression flags): (uncOff, uncSize, compOff, compSize)"""
    r = R(d); r.p = 0x71
    n = struct.unpack('<I', d[r.p:r.p+4])[0]
    return [struct.unpack('<4I', d[0x75+16*i:0x85+16*i]) for i in range(n)]

def unxor_block(b):
    """compressed block data: bytes [0x2a:] XORed with keystream derived from n=len-0x2a (FUN_004990c0(buf,len,0x2a))"""
    n = len(b) - 0x2a
    if n <= 0: return b
    k = (n*0x3b98d + 0x3aa29) & 0xffffffff; o = bytearray(b)
    for j in range(0x2a, len(b)):
        k %= 761; o[j] ^= KEY[k]; k += 1
    return bytes(o)

def read_chunk(d, c):
    """returns uncompressed bytes of a chunk (standard UE3 chunk header, LZO1X blocks, each block xored)"""
    sys.path.insert(0, HERE); import lzo1x
    tag, bs, cs, us = struct.unpack('<4I', d[c[2]:c[2]+16]); assert tag == 0x9e2a83c1
    nb = (us + bs - 1)//bs
    bl = struct.unpack('<%dI' % (2*nb), d[c[2]+16:c[2]+16+8*nb]); p = c[2]+16+8*nb; out = []
    for i in range(nb):
        out.append(lzo1x.decompress(unxor_block(d[p:p+bl[2*i]]))); p += bl[2*i]
    return b''.join(out)

def names(d, h):
    ch = chunks(d)[0]; u = read_chunk(d, ch); assert ch[0] == h['nameoff']
    p = 0; out = []
    for _ in range(h['namecount']):
        n = struct.unpack('<i', u[p:p+4])[0]; p += 4
        if n > 0: out.append(u[p:p+n-1].decode('latin1')); p += n
        else: out.append(u[p:p-2*n-2].decode('utf-16le')); p += -2*n
        p += 8
    return out

def write_plain(d, out_path):
    """Write a plain UE3 package: tag C1832A9E, plain header (compression flags 0, empty chunk table),
    summary tail (package source, texture allocations; plaintext in the original) kept, chunks at uncompressed offsets."""
    r = R(d); r.p = 4; hdr = bytearray(b'\xc1\x83\x2a\x9e')
    def f32():
        hdr.extend(struct.pack('<I', r.u32()))
    f32(); f32()                                   # ver, headersize
    n = r.i32(); hdr.extend(struct.pack('<i', n)); hdr.extend(r.raw(n))   # folder FString (len + data, separately xored)
    for _ in range(12): f32()          # flags, names(2), exports(2), imports(2), depends, ieg off, ieg cnt, eguid cnt, thumb
    for _ in range(4): f32()                       # GUID
    g = r.u32(); hdr.extend(struct.pack('<I', g))
    for _ in range(3*g): f32()                     # generations
    f32(); f32(); r.u32(); hdr.extend(struct.pack('<I', 0))   # engine ver, cooker ver, compression flags -> 0
    assert r.p == 0x71, hex(r.p)
    ch = chunks(d); hdr.extend(struct.pack('<I', 0))          # empty chunk table
    tail_end = min(c[2] for c in ch)                         # summary tail is plaintext up to first compressed chunk
    hdr.extend(d[0x75+16*len(ch):tail_end])
    assert len(hdr) == ch[0][0], (len(hdr), ch[0][0])
    with open(out_path, 'wb') as o:
        o.write(hdr)
        for i, c in enumerate(ch):
            u = read_chunk(d, c); assert len(u) == c[1], i
            o.seek(c[0]); o.write(u)
            if i % 20 == 0: print('chunk', i, flush=True)

if __name__ == '__main__':
    m, pkg = sys.argv[1:3]
    d = open(pkg, 'rb').read(); h = header(d)
    print({k: (hex(v) if isinstance(v, int) else v) for k, v in h.items()})
    print(len(chunks(d)), 'chunks')
    if m == 'plain': write_plain(d, sys.argv[3]); sys.exit()
    if m == 'names':
        nm = names(d, h); print(len(nm), 'names; first:', nm[:5])
        if len(sys.argv) > 3: open(sys.argv[3], 'w', encoding='utf-8').write(chr(10).join(nm))
