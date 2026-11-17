"""jsonkeys.py PE startVA length -> condensed list of: KEY [convertTo=N] accessor-call ; plus other calls. Accessors: jsoncpp helpers."""
import pefile,sys,re
from capstone import *
f=sys.argv[1]; s=int(sys.argv[2],16); ln=int(sys.argv[3],16)
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
md=Cs(CS_ARCH_X86,CS_MODE_32)
ins=list(md.disasm(d[va2off(s):va2off(s)+ln],s))
names={0x1008fa00:'[]',0x1008fa20:'[]nc',0x1008f040:'type',0x1008f530:'isConv',0x1008f180:'asInt',0x1008f640:'size',0x1008f7a0:'[i]',0x1008f060:'asString',0x1008efc0:'assign',0x1008ef10:'~',0x1008ec00:'ctor'}
out=[];lastpush=None
for k,i in enumerate(ins):
    m=re.match(r'^0x([0-9a-f]{8})$',i.op_str)
    if i.mnemonic=='push' and m:
        st=cstr(int(m.group(1),16))
        if st and i.op_str!='' : out.append('"%s"'%st)
    elif i.mnemonic=='push' and re.match(r'^[0-9]$',i.op_str):
        out.append('#%s'%i.op_str)
    elif i.mnemonic=='call':
        m=re.match(r'^0x([0-9a-f]+)$',i.op_str)
        if m:
            a=int(m.group(1),16); out.append(names.get(a,'c_%x'%a))
        else: out.append('callind(%s)'%i.op_str)
    elif i.mnemonic in('je','jne','jg','jl','jle','jge','ja','jb','jae','jbe') :
        out.append('%s>%s'%(i.mnemonic,i.op_str))
    elif i.mnemonic=='cmp' and re.search(r', (0x)?[0-9a-f]+$',i.op_str) and 'esp' not in i.op_str[:3]:
        out.append('cmp(%s)'%i.op_str)
print(' '.join(out))
