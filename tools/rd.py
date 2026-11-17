import pefile,sys
f=sys.argv[1]
pe=pefile.PE(f,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase;d=open(f,'rb').read()
def off(va):
    for s in pe.sections:
        a=base+s.VirtualAddress
        if a<=va<a+s.SizeOfRawData: return va-a+s.PointerToRawData
for a in sys.argv[2:]:
    va=int(a,16);o=off(va);print(a,d[o:o+40].split(b'\0')[0])
