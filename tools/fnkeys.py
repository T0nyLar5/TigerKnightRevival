"""fnkeys.py PE  -> for each function (split on int3 runs) list of referenced C strings (in order) + called functions count. Output: addr: s1,s2,..."""
import pefile,sys,re
from capstone import *
f=sys.argv[1]; pe=pefile.PE(f); base=pe.OPTIONAL_HEADER.ImageBase; d=open(f,'rb').read()
t=[s for s in pe.sections if s.Name.startswith(b'.text')][0]
tva=base+t.VirtualAddress; toff=t.PointerToRawData; tsz=t.SizeOfRawData
rd=[s for s in pe.sections if s.Name.startswith(b'.rdata')][0]
rva=base+rd.VirtualAddress; roff=rd.PointerToRawData; rsz=rd.SizeOfRawData
def cstr(va):
    if rva<=va<rva+rsz:
        o=va-rva+roff; e=d.find(b'\0',o,o+120)
        if e>o and all(32<=c<127 for c in d[o:e]): return d[o:e].decode()
md=Cs(CS_ARCH_X86,CS_MODE_32)
code=d[toff:toff+tsz]
funcs=[]; cur=None
# split by runs of >=2 int3
starts=[0]
for m in re.finditer(rb'\xcc{2,}',code):
    if m.end()<len(code): starts.append(m.end())
starts.append(len(code))
for a,b in zip(starts,starts[1:]):
    seg=code[a:b]; ss=[]
    for i in md.disasm(seg.rstrip(b'\xcc'),tva+a):
        m=re.match(r'.*0x([0-9a-f]{8})$',i.op_str)
        if m and i.mnemonic in('push','mov','lea'):
            s=cstr(int(m.group(1),16))
            if s: ss.append(s)
    print('%x(%d): %s'%(tva+a,b-a,'|'.join(ss)))
