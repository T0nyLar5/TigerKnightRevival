import sys,struct
cs={'blowfishP':struct.pack('<I',0x243F6A88),'blowfishP_be':struct.pack('>I',0x243F6A88),'tea':struct.pack('<I',0x9E3779B9),'tea2':struct.pack('<I',0x61C88647),
'aes_sbox':bytes([0x63,0x7c,0x77,0x7b,0xf2,0x6b]),'aes_te0':struct.pack('<I',0xc66363a5),'des_sp1':struct.pack('<I',0x01010400),'des_sp1b':struct.pack('<I',0x00808200),
'des_pc':bytes([57,49,41,33,25,17,9]),'des_ip':bytes([58,50,42,34,26,18,10,2]),'rc2':bytes([0xd9,0x78,0xf9,0xc4]),'md5':struct.pack('<I',0xd76aa478),'sha1':struct.pack('<I',0x67452301),'crc32':struct.pack('<I',0x77073096),'cast':struct.pack('<I',0x30fb40d4),'twofish':bytes([0xa9,0x67,0xb3,0xe8]),'rc4?':b'','sm4':bytes([0xd6,0x90,0xe9,0xfe,0xcc,0xe1]),'xxtea':struct.pack('<I',0x9e3779b9),'chacha':b'expand 32-byte k'}
for f in sys.argv[1:]:
    d=open(f,'rb').read()
    for k,v in cs.items():
        if not v: continue
        i=d.find(v)
        while i!=-1 and i<len(d):
            print(f.split('/')[-1],k,hex(i)); i=d.find(v,i+1)
