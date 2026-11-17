#!/usr/bin/env python3
"""Tiger Knight UE3 *.bin config codec (Kingdom-Win32-Shipping.exe: loader 0x445c00, xor routine 0x49ba60, SHA1 0x49a100).
File layout: u32 version(=1) | 20-byte SHA1 of PLAINTEXT payload | payload XOR-keystream (ANSI ini text).
Keystream: n = len(payload); k = (n*0x3b98d + 0x3aa29) & 0xffffffff; byte j uses KEY[(k + j) % 761]  (761-byte table at VA 0x15d6aa0 of the Win32 exe).
usage: uecfg.py dec IN.bin OUT.ini | enc IN.ini OUT.bin | extractkey EXE KEYFILE
The key table is read from tools/uecfg_key.bin (extracted once from the exe; 761 bytes)."""
import sys,hashlib,struct,os
KEYF=os.path.join(os.path.dirname(os.path.abspath(__file__)),'uecfg_key.bin')
def key(): return open(KEYF,'rb').read()
def xor(payload,K):
    n=len(payload); k=(n*0x3b98d+0x3aa29)&0xffffffff
    # exact emulation of: q=(k*0x561e46a5)>>40 ; k-=q*761 ; byte=K[k] ; k+=1
    out=bytearray(n)
    for j in range(n):
        q=(k*0x561e46a5)>>40
        r=(k-q*761)&0xffffffff
        out[j]=payload[j]^K[r]
        k=(r+1)&0xffffffff
    return bytes(out)
def dec(d):
    ver=struct.unpack('<I',d[:4])[0]; h=d[4:24]; p=xor(d[24:],key())
    return ver,hashlib.sha1(p).digest()==h,p
def enc(p):
    return struct.pack('<I',1)+hashlib.sha1(p).digest()+xor(p,key())
if __name__=='__main__':
    m=sys.argv[1]
    if m=='extractkey':
        import pefile
        pe=pefile.PE(sys.argv[2],fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase; d=open(sys.argv[2],'rb').read()
        for s in pe.sections:
            a=base+s.VirtualAddress
            if a<=0x15d6aa0<a+s.SizeOfRawData:
                o=0x15d6aa0-a+s.PointerToRawData; open(sys.argv[3],'wb').write(d[o:o+761]); print('ok',o)
    elif m=='dec':
        ver,ok,p=dec(open(sys.argv[2],'rb').read()); open(sys.argv[3],'wb').write(p); print('ver',ver,'sha1 ok',ok,len(p),'bytes')
    elif m=='enc':
        open(sys.argv[3],'wb').write(enc(open(sys.argv[2],'rb').read()))
