"""schema.py PE funcVA tableVA count [case-indices...] -> per-case json field schema (key:type/accessor)"""
import pefile,sys,re,struct,subprocess
from capstone import *
f=sys.argv[1]; fva=int(sys.argv[2],16); tva=int(sys.argv[3],16); n=int(sys.argv[4]); want=[int(x) for x in sys.argv[5:]]
pe=pefile.PE(f); base=pe.OPTIONAL_HEADER.ImageBase; d=open(f,'rb').read()
def va2off(va):
    for sec in pe.sections:
        a=base+sec.VirtualAddress
        if a<=va<a+sec.SizeOfRawData: return va-a+sec.PointerToRawData
def cstr(va):
    o=va2off(va)
    if o is None: return None
    e=d.find(b'\0',o,o+120)
    if e>o and all(32<=c<127 for c in d[o:e]): return d[o:e].decode()
tbl=struct.unpack('<%dI'%n,d[va2off(tva):va2off(tva)+4*n]); ends=sorted(set(tbl))
md=Cs(CS_ARCH_X86,CS_MODE_32)
ACC={0x1008f180:'int',0x1008f2b0:'uint',0x1008f050:'cstr',0x1008f060:'str',0x1008f640:'ARRAY'}
def case(idx):
    t=tbl[idx]; nx=[e for e in ends if e>t]; end=nx[0] if nx else t+0x2000
    ins=list(md.disasm(d[va2off(t):va2off(t)+end-t],t))
    toks=[]
    for i in ins:
        m=re.match(r'^0x([0-9a-f]{8})$',i.op_str)
        if i.mnemonic=='push' and m:
            s=cstr(int(m.group(1),16))
            if s: toks.append(('K',s))
        elif i.mnemonic=='push' and re.match(r'^\d$',i.op_str): toks.append(('N',int(i.op_str)))
        elif i.mnemonic=='call':
            m=re.match(r'^0x([0-9a-f]+)$',i.op_str)
            toks.append(('C',int(m.group(1),16) if m else 0))
        elif i.mnemonic=='cmp' and ', 6' == i.op_str[-3:]: toks.append(('ARR6',0))
    return toks
for idx in want:
    toks=case(idx); out=[]; i=0; seen=set()
    while i<len(toks):
        k,v=toks[i]
        if k=='K':
            # pattern: K [] ... ; find accessor: next C after K within next 3 tokens
            j=i+1; 
            nxt=toks[i+1:i+4]
            acc=[x for x in nxt if x[0]=='C']
            a=ACC.get(acc[1][1]) if len(acc)>1 else None
            # detect isConv type: previous N
            conv=toks[i-1][1] if i>0 and toks[i-1][0]=='N' else None
            out.append((v,conv,[ACC.get(c[1],hex(c[1])) for c in acc]))
        i+=1
    print('== case',idx,hex(tbl[idx]))
    # dedupe: keep entries having conv (the isConv test) or ARRAY/size
    res=[];prev=None
    for v,conv,acc in out:
        if conv is not None and acc and acc[0]=='[]'.replace('[]','') : pass
    # print raw dedup of consecutive
    last=None
    lines=[]
    for v,conv,acc in out:
        tag='%s%s %s'%(v,(':T%d'%conv) if conv is not None else '',','.join(a for a in acc if a not in('0x1008fa00','0x1008f040','0x1008f530')))
        if v!=last: lines.append(tag); last=v
        else: lines[-1]=tag if conv is not None or 'int' in tag or 'str' in tag else lines[-1]
    print('  '+' | '.join(lines))
