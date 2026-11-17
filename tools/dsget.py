#!/usr/bin/env python3
"""List DataSet getter indices used by a function: `mov r,[x+4]` (vtable slot 1) followed within 3 insns by `push imm` then call r.
usage: dsget.py <pe> <hexva> [<hexva>...]"""
import pefile, sys, re
from capstone import *
f = sys.argv[1]
pe = pefile.PE(f, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
d = open(f, 'rb').read()
def off(va):
    for s in pe.sections:
        a = base + s.VirtualAddress
        if a <= va < a + s.Misc_VirtualSize:
            return va - a + s.PointerToRawData
md = Cs(CS_ARCH_X86, CS_MODE_32)
for a in sys.argv[2:]:
    va = int(a, 16)
    o = off(va)
    ins = []
    for i in md.disasm(d[o:o + 0x6000], va):
        ins.append(i)
        if i.mnemonic == 'ret' and len(ins) > 5:
            p = o + (i.address + i.size - va)
            if d[p:p + 1] in (b'\xcc', b'\x90'):
                break
    res = set()
    for k, i in enumerate(ins):
        m = re.match(r'^(\w+), dword ptr \[(\w+) \+ 4\]$', i.op_str) if i.mnemonic == 'mov' else None
        if m:
            for j in range(k + 1, min(k + 4, len(ins))):
                if ins[j].mnemonic == 'push' and re.match(r'^(0x[0-9a-f]+|\d+)$', ins[j].op_str):
                    res.add(int(ins[j].op_str, 0))
                    break
    print(a, 'size', ins[-1].address - va, 'idx:', [hex(x) for x in sorted(res)])
