import pefile,sys,struct
from capstone import *
f=sys.argv[1]; targets=[bytes.fromhex(x) if False else x.encode() for x in sys.argv[2:]]
pe=pefile.PE(f); d=open(f,'rb').read(); base=pe.OPTIONAL_HEADER.ImageBase
def off2va(o):
    for s in pe.sections:
        if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData: return base+s.VirtualAddress+o-s.PointerToRawData
for t in targets:
    i=d.find(t+b'\0')
    while i!=-1:
        va=off2va(i); print(t,hex(i),hex(va))
        pat=struct.pack('<I',va); j=d.find(pat)
        while j!=-1:
            print('  ref at file',hex(j),hex(off2va(j)) if off2va(j) else None); j=d.find(pat,j+1)
        i=d.find(t+b'\0',i+1)
