"""routemap.py PoClientDLL.dll -> route index, name, xref VA(s) of the route-table slot in code"""
import struct,pefile,sys
f=sys.argv[1]; pe=pefile.PE(f); d=open(f,'rb').read(); base=pe.OPTIONAL_HEADER.ImageBase
def va2off(va):
    for s in pe.sections:
        a=base+s.VirtualAddress
        if a<=va<a+s.SizeOfRawData: return va-a+s.PointerToRawData
def off2va(o):
    for s in pe.sections:
        if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData: return base+s.VirtualAddress+o-s.PointerToRawData
def cs(va):
    o=va2off(va); e=d.find(b'\0',o); return d[o:e].decode()
t0=0x101a2040
text=[s for s in pe.sections if s.Name.startswith(b'.text')][0]
for k in range(0,0xf4+0x20):
    slot=t0+4*k; o=va2off(slot); v=struct.unpack('<I',d[o:o+4])[0]
    try: n=cs(v)
    except: break
    refs=[];pat=struct.pack('<I',slot); j=d.find(pat,text.PointerToRawData,text.PointerToRawData+text.SizeOfRawData)
    while j!=-1: refs.append(hex(off2va(j))); j=d.find(pat,j+1,text.PointerToRawData+text.SizeOfRawData)
    print(k,n,' '.join(refs))
