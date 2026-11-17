#!/usr/bin/env python3
"""Tiger Knight config.cfg / config_client.cfg / terrain.cfg codec (Sync.dll EyptFiles / CEncrypt<32,253,7,31,122,207,229,63>,
Sync.dll 0x100b9f20 key init, 0x100b9fa0 xor).  Same keystream as the SyncClient TCP stream cipher:
ks[n] = A[n%256] ^ B[(n//256)%256].   usage: cfgdec.py in out"""
import sys
def tables():
    a=[];x=0x1f
    for _ in range(256):
        a.append(x); x=((((x<<5)&0xff)+0xfd)*x+7)&0xff
    b=[];c=0x3f
    for _ in range(256):
        b.append(c); c=((((c*0x7a)&0xff)-0x31)*c-0x1b)&0xff
    return a,b
A,B=tables()
def xor(d, start=0):
    return bytes(c ^ A[(start+i)&255] ^ B[((start+i)>>8)&255] for i,c in enumerate(d))
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read()
    open(sys.argv[2],'wb').write(xor(d))

def unpack(dec, outdir):
    """decrypted pack = repeated:  <win path> <size>\r\n <size bytes> \r\n   -> files under outdir (basename only, dedup by folder)"""
    import os
    off=0; n=0; names=[]
    while off < len(dec):
        e=dec.find(b'\r\n', off)
        if e<0 or e-off>600: break
        hdr=dec[off:e].decode('utf-8','replace')
        try:
            path,size=hdr.rsplit(' ',1); size=int(size)
        except Exception:
            print('bad header at',off,repr(dec[off:off+80])); break
        body=dec[e+2:e+2+size]
        rel=path.replace(chr(92),'/').split('/')
        rel='/'.join(rel[-2:]) if len(rel)>1 else rel[-1]
        p=os.path.join(outdir,rel); os.makedirs(os.path.dirname(p),exist_ok=True)
        open(p,'wb').write(body); names.append((rel,size)); n+=1
        off=e+2+size+2
    return names
