#!/usr/bin/env python3
"""Minimal UE3 (v865) plain-package export reader, for tools/upatch.py. Works on the plain .u from updec.py."""
import struct, mmap

class Pkg:
    def __init__(s, path):
        s.f = open(path, 'rb'); s.m = mmap.mmap(s.f.fileno(), 0, access=mmap.ACCESS_READ); m = s.m
        assert m[:4] == b'\xc1\x83\x2a\x9e'
        p = 12; n = struct.unpack_from('<i', m, p)[0]; p += 4 + n
        (s.flags, s.ncount, s.noff, s.ecount, s.eoff, s.icount, s.ioff) = struct.unpack_from('<7I', m, p)
        s.names = []; p = s.noff
        for _ in range(s.ncount):
            n = struct.unpack_from('<i', m, p)[0]; p += 4
            if n > 0: s.names.append(m[p:p+n-1].decode('latin1')); p += n
            else: s.names.append(m[p:p-2*n-2].decode('utf-16le')); p += -2*n
            p += 8
        s.imports = []; p = s.ioff
        for _ in range(s.icount):
            s.imports.append(struct.unpack_from('<iiiiiiii', m, p)[:8]); p += 28 if False else 28
        s.exports = []; p = s.eoff
        for _ in range(s.ecount):
            cls, sup, outer, nm, nn, arch = struct.unpack_from('<6i', m, p)
            flags, size, off, eflags, nnet = struct.unpack_from('<QiiIi', m, p+24)
            q = p + 24 + 8 + 4 + 4 + 4 + 4 + 4*nnet + 16 + 4
            s.exports.append(dict(cls=cls, sup=sup, outer=outer, name=s.names[nm], num=nn, size=size, off=off, entry=p))
            p = q
    def objname(s, idx):
        if idx > 0: return s.exports[idx-1]['name']
        if idx < 0: return s.names[s.imports[-idx-1][5]]
        return ''
    def path(s, i):
        e = s.exports[i]; o = e['outer']
        return (s.path(o-1) + '.' if o > 0 else '') + e['name']
    def find(s, path):
        return [i for i, e in enumerate(s.exports) if e['name'] == path.split('.')[-1] and s.path(i) .endswith(path)]
    def data(s, i):
        e = s.exports[i]; return s.m[e['off']:e['off']+e['size']]
