#!/usr/bin/env python3
"""Tiger Knight .dat codec (frontend.exe 0xa45790).
key[i] = rand()&0xff for i in 0..127 after srand(0x2537) (MSVC LCG).
decrypt: t = c ^ key[i%128]; p = rotr8(t, i%8)
encrypt: t = rotl8(p, i%8); c = t ^ key[i%128]
usage: tkcrypt.py dec|enc in out"""
import sys
def keytab(seed=0x2537):
    s=seed; k=[]
    for _ in range(128):
        s=(s*214013+2531011)&0xffffffff
        k.append(((s>>16)&0x7fff)&0xff)
    return k
K=keytab()
def rotr(b,n): return ((b>>n)|(b<<(8-n)))&0xff
def rotl(b,n): return ((b<<n)|(b>>(8-n)))&0xff
def dec(d): return bytes(rotr(c^K[i%128],i%8) for i,c in enumerate(d))
def enc(d): return bytes(rotl(p,i%8)^K[i%128] for i,p in enumerate(d))
if __name__=='__main__':
    m,a,b=sys.argv[1:4]
    d=open(a,'rb').read()
    open(b,'wb').write((dec if m=='dec' else enc)(d))
