"""dx.py PE xref STRING [window]   -> code xrefs to string (exact C-string) with context
   dx.py PE dis VA N               -> disassemble N insns
   dx.py PE func VA                -> disassemble to next 'ret' padding (int3) boundary, annotating string refs"""
import pefile,sys,struct,re
from capstone import *
f=sys.argv[1]; pe=pefile.PE(f); base=pe.OPTIONAL_HEADER.ImageBase; d=open(f,'rb').read()
secs=[(base+s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,s.Name.rstrip(b'\0').decode()) for s in pe.sections]
def va2off(va):
    for a,vs,po,rs,n in secs:
        if a<=va<a+min(vs,rs) : return va-a+po
def off2va(o):
    for a,vs,po,rs,n in secs:
        if po<=o<po+rs: return a+o-po
def cstr(va,mx=80):
    o=va2off(va)
    if o is None: return None
    e=d.find(b'\0',o,o+mx)
    if e<0: return None
    s=d[o:e]
    if len(s)>=1 and all(32<=c<127 for c in s): return s.decode()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
def dis(va,n=None,end=None):
    o=va2off(va); out=[]
    for i in md.disasm(d[o:o+0x4000],va):
        ann=''
        m=re.search(r'0x([0-9a-f]{5,8})\b',i.op_str)
        if m:
            s=cstr(int(m.group(1),16))
            if s: ann='   ; "%s"'%s
        out.append('%x: %s %s%s'%(i.address,i.mnemonic,i.op_str,ann))
        if n and len(out)>=n: break
        if end and i.address>=end: break
    return out
cmd=sys.argv[2]
if cmd=='xref':
    t=sys.argv[3].encode(); w=int(sys.argv[4]) if len(sys.argv)>4 else 0
    i=d.find(b'\0'+t+b'\0')
    while i!=-1:
        va=off2va(i+1); pat=struct.pack('<I',va)
        print('string at',hex(va))
        for a,vs,po,rs,n in secs:
            if n!='.text' and not n.startswith('.text'): continue
            j=d.find(pat,po,po+rs)
            while j!=-1:
                print('  xref',hex(off2va(j)))
                j=d.find(pat,j+1,po+rs)
        i=d.find(b'\0'+t+b'\0',i+1)
elif cmd=='dis':
    print('\n'.join(dis(int(sys.argv[3],16),int(sys.argv[4]))))
elif cmd=='func':
    va=int(sys.argv[3],16); n=int(sys.argv[4]) if len(sys.argv)>4 else 4000
    lines=dis(va,n)
    # stop at int3 run
    for l in lines:
        print(l)
        if ' int3' in l: break
