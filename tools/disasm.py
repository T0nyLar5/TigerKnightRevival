import pefile,sys
from capstone import *
f=sys.argv[1]; start=int(sys.argv[2],16); n=int(sys.argv[3])
pe=pefile.PE(f); base=pe.OPTIONAL_HEADER.ImageBase
def va2off(va):
    for s in pe.sections:
        a=base+s.VirtualAddress
        if a<=va<a+s.SizeOfRawData: return va-a+s.PointerToRawData
d=open(f,'rb').read()
o=va2off(start)
md=Cs(CS_ARCH_X86,CS_MODE_32)
for i in md.disasm(d[o:o+n*8],start):
    print(hex(i.address),i.mnemonic,i.op_str)
    n-=1
    if n<=0:break
