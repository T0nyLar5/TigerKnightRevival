#!/usr/bin/env python3
"""pushkeys.py PE startVA endVA -> ordered list of (json key, value accessor) from a PoClientDLL parse function."""
import pefile, sys, re
from capstone import *
f = sys.argv[1]; start = int(sys.argv[2], 16); end = int(sys.argv[3], 16)
pe = pefile.PE(f); base = pe.OPTIONAL_HEADER.ImageBase; d = open(f, 'rb').read()
def v2o(va):
    for s in pe.sections:
        a = base + s.VirtualAddress
        if a <= va < a + s.SizeOfRawData: return va - a + s.PointerToRawData
def cstr(va):
    o = v2o(va)
    if o is None: return None
    e = d.find(b'\0', o, o + 80)
    if e > o and all(32 <= c < 127 for c in d[o:e]): return d[o:e].decode()
ACC = {0x1008f180: 'int', 0x1008f2b0: 'uint', 0x1008f050: 'cstr', 0x1008f060: 'str', 0x1008f4c0: 'bool', 0x1008f640: 'ARRAY', 0x1008f530: None, 0x1008f040: None, 0x1008fa00: None}
md = Cs(CS_ARCH_X86, CS_MODE_32)
o = v2o(start); cur = None; out = []
for i in md.disasm(d[o:o + (end - start)], start):
    m = re.match(r'^0x([0-9a-f]{6,8})$', i.op_str)
    if i.mnemonic == 'push' and m:
        t = cstr(int(m.group(1), 16))
        if t and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t):
            cur = t
    if i.mnemonic == 'call':
        m2 = re.match(r'^0x([0-9a-f]+)$', i.op_str)
        if m2:
            a = int(m2.group(1), 16)
            if a in ACC and ACC[a] and cur:
                out.append((cur, ACC[a])); cur = None
            elif a not in ACC and cur and a != 0:
                pass
seen = []
for k, t in out:
    if not seen or seen[-1] != (k, t): seen.append((k, t))
print(' '.join('%s:%s' % x for x in seen))
