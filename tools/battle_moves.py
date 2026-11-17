r"""Per-second decode of 0x2721/2737/2738/2739/2722 (client move reports). Usage: tools.venvScriptspython.exe -I toolsbattle_moves.py <battleserver log>. y = vertical (up), x/z horizontal; 2721 and 2738 mode2 = velocity f16, 2737 = position f32."""
import re,struct,sys,collections
def uv(b,i):
    r=0;s=0
    while 1:
        c=b[i];i+=1;r|=(c&0x7f)<<s;s+=7
        if c<0x80:return r,i
def h(b,i):return struct.unpack('<e',b[i:i+2])[0]
t0=None
rows=[]
for line in open(sys.argv[1],encoding='utf-8',errors='replace'):
    m=re.match(r"(\d\d):(\d\d):(\d\d)\.(\d+) RECV .*?type_0x(2721|2737|2738|2739|2722) body=([0-9a-f ]*)",line)
    if not m:
        m2=re.match(r"(\d\d):(\d\d):(\d\d)\.(\d+) TCP CONNECT",line)
        if m2:t0=int(m2[1])*3600+int(m2[2])*60+int(m2[3])+int(m2[4])/1000
        continue
    t=int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000-(t0 or 0)
    ty=m[5];b=bytes.fromhex(m[6].replace(' ',''))
    uid,i=uv(b,0)
    if ty=='2721':d=tuple(round(h(b,i+2*k),3) for k in range(3))
    elif ty=='2737':d=tuple(round(struct.unpack('<f',b[i+4*k:i+4*k+4])[0],2) for k in range(3))
    elif ty=='2738':
        md,j=uv(b,i);d=(md,)+tuple(round(h(b,j+2*k),3) for k in range(3))
    elif ty=='2739':d=(uv(b,i)[0],)
    else:d=tuple(b[i:])
    rows.append((t,ty,d))
# per second summary
by=collections.defaultdict(list)
for t,ty,d in rows:by[int(t)].append((ty,d))
for s in sorted(by):
    ev=by[s];out=[]
    for ty in ('2721','2737','2738','2739','2722'):
        x=[d for tt,d in ev if tt==ty]
        if not x:continue
        if ty in('2721','2737'):
            xs=[(a[0]) for a in x];ys=[a[1] for a in x];zs=[a[2] for a in x]
            out.append(f"{ty} n={len(x)} x[{min(xs)},{max(xs)}] y[{min(ys)},{max(ys)}] z[{min(zs)},{max(zs)}]")
        else:
            out.append(f"{ty} n={len(x)} uniq={sorted(set(x))[:6]}")
    print(s,' | '.join(out))
