"""msg_catalog.py <SyncClient.dll Win32> -> JSON [{name,vtables,sites,ids:[[id,votes]]}].
RTTI exists only for boost sp_counted_impl_p<UMsgX>. For each, find code that stores that vtable
(mov [reg],vtable) and look BEFORE it (MsgX ctor, inlined or called) for 'mov [reg+off], imm' of a
plausible message id (0x3e9..0x6000). Heuristic: ids = candidates ranked by votes (H, verify by decompile)."""
import pefile,sys,re,struct,json,bisect
from capstone import *
f=sys.argv[1]; pe=pefile.PE(f); base=pe.OPTIONAL_HEADER.ImageBase; d=open(f,'rb').read()
secs=[(s.Name.rstrip(b'\0').decode(),base+s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def o2v(o):
    for n,a,vs,po,rs in secs:
        if po<=o<po+rs: return o-po+a
text=[s for s in secs if s[0]=='.text'][0]
tdata=d[text[3]:text[3]+text[4]]
md=Cs(CS_ARCH_X86,CS_MODE_32)
tds={}
for m in re.finditer(rb'\.\?AV\?\$sp_counted_impl_p@U(Msg\w+?)@@@detail@boost@@\x00',d):
    tds[o2v(m.start()-8)]=m.group(1).decode()
# one pass: locate all COL (sig 0) pointing at a TD, then vtables pointing at COLs
tdset={struct.pack('<I',k):v for k,v in tds.items()}
col={}
for m in re.finditer(rb'\x00\x00\x00\x00.{8}(....)',d[:text[3]+0] if False else d,re.S):
    pass
rd=[s for s in secs if s[0]=='.rdata'][0]
rdata=d[rd[3]:rd[3]+rd[4]]
for i in range(0,len(rdata)-16,4):
    if rdata[i:i+4]==b'\0\0\0\0' and rdata[i+12:i+16] in tdset:
        col[rd[1]+i]=tdset[rdata[i+12:i+16]]
vt={}
for i in range(0,len(rdata)-4,4):
    v=struct.unpack('<I',rdata[i:i+4])[0]
    if v in col: vt.setdefault(col[v],set()).add(rd[1]+i+4)
ID=re.compile(r'^(?:word|dword) ptr \[\w+(?: \+ 0x[0-9a-f]+)?\], (0x[0-9a-f]+)$')
def ids_in(start,length):
    out=[]
    for i in md.disasm(tdata[max(0,start):start+length],text[1]+max(0,start)):
        if i.mnemonic=='mov':
            mm=ID.match(i.op_str)
            if mm and 0x3e8<=int(mm.group(1),16)<0x6000: out.append(int(mm.group(1),16))
    return out
# index all code sites storing any vtable: scan for C7 xx <vtable>
vtall={}
for n,s in vt.items():
    for a in s: vtall[a]=n
sites={}
for p in range(len(tdata)-6):
    if tdata[p]==0xC7:
        for q in (p+2,p+3,p+6):   # modrm / modrm+disp8 / modrm+sib+...
            if q+4<=len(tdata):
                v=struct.unpack('<I',tdata[q:q+4])[0]
                if v in vtall: sites.setdefault(vtall[v],[]).append(p)
# --- registry: init fn pushes (func2, func1, id) then calls REG; map id -> class via sp_counted site inside funcs
REG=0x10092c10
INIT=0x10093050
def fend(p):
    q=p+1
    while q<len(tdata)-1 and not (tdata[q]==0xCC and tdata[q+1]==0xCC): q+=1
    return q
site2name={}
for n,l in sites.items():
    for p in l: site2name[p]=n
sorted_sites=sorted(site2name)
def classes_in(va,depth=1):
    p=va-text[1]; e=fend(p); found=set()
    for sp in sorted_sites:
        if p<=sp<e: found.add(site2name[sp])
    if not found and depth>0:
        for i in md.disasm(tdata[p:e],va):
            if i.mnemonic=='call' and i.op_str.startswith('0x'):
                t=int(i.op_str,16)
                if text[1]<=t<text[1]+len(tdata): found|=classes_in(t,depth-1)
    return found
ins=list(md.disasm(tdata[INIT-text[1]:INIT-text[1]+0x4000],INIT))
regs=[];pushes=[]
for i in ins:
    if i.mnemonic=='push' and i.op_str.startswith('0x'): pushes.append(int(i.op_str,16))
    elif i.mnemonic=='call':
        if i.op_str==hex(REG) and len(pushes)>=3:
            idv,f1,f2=pushes[-1],pushes[-2],pushes[-3]
            regs.append((idv,f1,f2))
        pushes=[]
    elif i.mnemonic=='ret': break
# Verified pattern (ids known from battle_proto): the class's shared_ptr ctor (holding the sp_counted
# vtable store) is the LAST site located below the larger of the two registered codec funcs (decoder).
site_va=sorted((text[1]+p,n) for n,l in sites.items() for p in l)
sv_addrs=[a for a,_ in site_va]
res=[]
for idv,f1,f2 in regs:
    hi=max(f1,f2); k=bisect.bisect_left(sv_addrs,hi)-1
    cl=[]
    if k>=0 and hi-sv_addrs[k]<0x600: cl=[site_va[k][1]]
    res.append({'id':idv,'dec':hex(hi),'enc':hex(min(f1,f2)),'classes':cl,'site':hex(sv_addrs[k]) if cl else None})
print(json.dumps(res))
