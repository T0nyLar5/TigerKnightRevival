"""cases.py PE funcVA tableVA count -> for each switch case, list strings referenced in that case's code range (to the next case start)"""
import pefile,sys,struct,re
from capstone import *
f=sys.argv[1]; fva=int(sys.argv[2],16); tva=int(sys.argv[3],16); n=int(sys.argv[4])
pe=pefile.PE(f); base=pe.OPTIONAL_HEADER.ImageBase; d=open(f,'rb').read()
def va2off(va):
    for s in pe.sections:
        a=base+s.VirtualAddress
        if a<=va<a+s.SizeOfRawData: return va-a+s.PointerToRawData
def cstr(va):
    o=va2off(va)
    if o is None: return None
    e=d.find(b'\0',o,o+120)
    if e>o and all(32<=c<127 for c in d[o:e]): return d[o:e].decode()
o=va2off(tva); tbl=struct.unpack('<%dI'%n,d[o:o+4*n])
ends=sorted(set(tbl))
md=Cs(CS_ARCH_X86,CS_MODE_32)
# function end: find int3 run after fva
code=d[va2off(fva):va2off(fva)+0x40000]
m=re.search(rb'\xcc\xcc',code[ (max(tbl)-fva) :]); fend=max(tbl)+ (m.start() if m else 0x2000)
# but jump table typically after func; use fend = table va
fend=min(tva, fend) if tva>fva else fend
res={}
for idx,t in enumerate(tbl):
    nxt=[e for e in ends if e>t]
    end=nxt[0] if nxt else fend
    ss=[]
    for i in md.disasm(d[va2off(t):va2off(t)+(end-t)],t):
        m=re.match(r'.*0x([0-9a-f]{8})$',i.op_str)
        if m and i.mnemonic in('push','mov'):
            s=cstr(int(m.group(1),16))
            if s and (not ss or ss[-1]!=s): ss.append(s)
    print(idx,hex(t),hex(end-t),'|'.join(ss))
